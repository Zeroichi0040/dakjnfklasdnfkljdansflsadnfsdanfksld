"""Readiness checks include the applied migration head, not just an open port."""

from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from backend.config import ROOT
from database import db


def assert_ready():
    db.session.execute(text("SELECT id FROM site_state WHERE id = 1")).scalar_one()
    applied = set(MigrationContext.configure(db.session.connection()).get_current_heads())
    expected = set(ScriptDirectory(str(ROOT / "database/migrations")).get_heads())
    if applied != expected:
        raise RuntimeError("Database migrations are pending. Run python manage.py db upgrade.")
    return expected
