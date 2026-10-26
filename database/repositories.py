"""Shared database queries. Resource queries live in backend/framework/services.py."""

from database import db
from database.models import AuditEvent, User


def user_by_email(email):
    return db.session.scalar(db.select(User).where(User.email == email.strip().casefold()))


def events_query(user_id):
    return db.select(AuditEvent).where(AuditEvent.user_id == user_id).order_by(AuditEvent.id.desc())
