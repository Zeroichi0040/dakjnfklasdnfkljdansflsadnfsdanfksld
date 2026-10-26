"""Session authentication, discovery, generated OpenAPI, and private file APIs."""

from flask import Blueprint, abort, jsonify, render_template, request, session
from flask_login import current_user, login_required, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.orm import defer

from backend.common.errors import ValidationError
from backend.extensions import limiter
from backend.framework.extension import framework
from backend.framework.openapi import specification
from backend.framework.routes import json_payload, pagination_values
from backend.framework.services import encode
from backend.modules.auth.forms import LoginForm
from backend.modules.auth.routes import login_limit_key
from backend.modules.auth.service import authenticate, start_session
from backend.modules.files.service import remove_image, store_image
from database import db
from database.models import Attachment

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/v1/csrf")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@bp.post("/v1/auth/login")
@limiter.limit("10 per minute;50 per hour", key_func=login_limit_key)
@limiter.limit("120 per minute")
def login_api():
    data = json_payload()
    if not isinstance(data.get("email"), str) or not isinstance(data.get("password"), str):
        raise ValidationError({"credentials": ["Send email and password as text."]})
    form = LoginForm(data=data)
    if not form.validate():
        raise ValidationError(form.errors)
    user = authenticate(form.email.data, form.password.data)
    if not user:
        abort(401, description="Email or password is incorrect.")
    start_session(user)
    return jsonify(
        user={"id": user.id, "display_name": user.display_name, "role": user.role}, csrf_token=generate_csrf()
    )


@bp.post("/v1/auth/logout")
@login_required
def logout_api():
    logout_user()
    session.clear()
    return "", 204


@bp.get("/v1/me")
@login_required
def me():
    return jsonify(
        id=current_user.id, display_name=current_user.display_name, email=current_user.email, role=current_user.role
    )


@bp.get("/v1/resources")
@login_required
def resources():
    return jsonify(
        data=[
            {
                "key": r.key,
                "label": r.label,
                "url": f"/api/v1/{r.key}",
                "fields": [{"name": f.name, "type": f.kind, "required": f.required} for f in r.fields],
            }
            for r in framework().resources.values()
            if r.policy.allows(current_user)
        ]
    )


def attachment_json(record):
    return {
        "id": record.id,
        "filename": record.filename,
        "content_type": record.content_type,
        "size": record.size,
        "created_at": encode(record.created_at),
        "download_url": f"/files/{record.id}/download",
    }


@bp.get("/v1/files")
@login_required
def files_list():
    page, size = pagination_values()
    statement = (
        db.select(Attachment)
        .options(defer(Attachment.data))
        .where(Attachment.user_id == current_user.id)
        .order_by(Attachment.created_at.desc())
    )
    result = db.paginate(statement, page=page, per_page=size, error_out=False)
    return jsonify(
        data=[attachment_json(a) for a in result.items],
        pagination={"page": page, "per_page": size, "total": result.total, "pages": result.pages},
    )


@bp.post("/v1/files")
@login_required
@limiter.limit("20 per hour")
def files_upload():
    record = store_image(current_user.id, request.files.get("file"))
    return jsonify(data=attachment_json(record)), 201


@bp.delete("/v1/files/<uuid:identifier>")
@login_required
def files_delete(identifier):
    remove_image(current_user.id, str(identifier))
    return "", 204


@bp.get("/openapi.json")
def openapi():
    return jsonify(specification(framework().resources.values()))


@bp.get("/docs")
def docs():
    return render_template("public/api_docs.html", resources=framework().resources.values())
