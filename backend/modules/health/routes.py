from flask import Blueprint, jsonify
from sqlalchemy.exc import SQLAlchemyError

from backend.framework.readiness import assert_ready
from database import db

bp = Blueprint("health", __name__)


@bp.get("/health")
@bp.get("/health/live")
def live():
    # No database query: health polling should not keep a free database awake.
    return jsonify(status="ok", app="flask-fullstack-framework", version="3.0.0")


@bp.get("/health/ready")
def ready():
    try:
        assert_ready()
    except (SQLAlchemyError, RuntimeError):
        db.session.rollback()
        return jsonify(status="unavailable"), 503
    return jsonify(status="ready")
