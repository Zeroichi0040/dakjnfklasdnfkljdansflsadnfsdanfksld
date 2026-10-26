"""Transactions, owner scopes, optimistic locking, and hooks for every resource."""

from datetime import date, datetime, timezone
from decimal import Decimal
from functools import wraps

from sqlalchemy import or_
from werkzeug.exceptions import Conflict, NotFound

from backend.common.errors import ValidationError
from backend.framework.validation import clean_payload
from database import db
from database.models import AuditEvent


def transactional(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:
            db.session.rollback()
            raise

    return wrapped


def query(resource, actor, search="", sort="-id"):
    statement = resource.policy.query(resource.model, actor)
    if search and resource.search:
        statement = statement.where(
            or_(*(getattr(resource.model, name).contains(search[:120], autoescape=True) for name in resource.search))
        )
    allowed = {"id", "created_at", "updated_at", *(f.name for f in resource.fields if f.kind != "textarea")}
    name = sort.lstrip("-")
    if name not in allowed:
        raise ValidationError({"sort": ["Choose a sortable declared field."]})
    column = getattr(resource.model, name)
    return statement.order_by(column.desc() if sort.startswith("-") else column.asc(), resource.model.id.desc())


def get_record(resource, actor, identifier):
    record = db.session.scalar(resource.policy.query(resource.model, actor).where(resource.model.id == identifier))
    if record is None:
        raise NotFound("That record is not available to your account.")
    return record


def require_version(record, value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (str, int))
        or len(str(value)) > 12
        or not str(value).isdigit()
        or int(value) < 1
    ):
        raise ValidationError({"version": ["Send the current record version."]})
    if record.version != int(value):
        raise Conflict("This record changed in another request. Reload and try again.")


@transactional
def create(resource, actor, payload):
    resource.policy.authorize(actor, "create")
    values = clean_payload(resource, payload)
    if "version" in payload:
        raise ValidationError({"version": ["The server assigns versions when creating a record."]})
    record = resource.model(user_id=actor.id, **values)
    if resource.on_save:
        resource.on_save(record, actor, True)
    db.session.add(record)
    db.session.flush()
    db.session.add(
        AuditEvent(user_id=actor.id, action=f"{resource.key}.created", subject=f"{resource.singular} #{record.id}")
    )
    db.session.commit()
    return record


@transactional
def update(resource, actor, identifier, payload):
    resource.policy.authorize(actor, "update")
    record = get_record(resource, actor, identifier)
    if not isinstance(payload, dict):
        raise ValidationError({"body": ["Send a JSON object."]})
    require_version(record, payload.get("version"))
    values = clean_payload(resource, payload, partial=True)
    if not values:
        raise ValidationError({"body": ["Send at least one editable field."]})
    for name, value in values.items():
        setattr(record, name, value)
    if resource.on_save:
        resource.on_save(record, actor, False)
    db.session.add(
        AuditEvent(user_id=actor.id, action=f"{resource.key}.updated", subject=f"{resource.singular} #{record.id}")
    )
    db.session.commit()
    return record


@transactional
def delete(resource, actor, identifier, version):
    resource.policy.authorize(actor, "delete")
    record = get_record(resource, actor, identifier)
    require_version(record, version)
    if resource.on_delete:
        resource.on_delete(record, actor)
    db.session.add(
        AuditEvent(user_id=actor.id, action=f"{resource.key}.deleted", subject=f"{resource.singular} #{record.id}")
    )
    db.session.delete(record)
    db.session.commit()


def encode(value):
    if isinstance(value, datetime):
        aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return aware.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, ".2f")
    return value


def serialize(resource, record):
    names = ["id", "version", "created_at", "updated_at", *(field.name for field in resource.fields)]
    return {name: encode(getattr(record, name)) for name in names}
