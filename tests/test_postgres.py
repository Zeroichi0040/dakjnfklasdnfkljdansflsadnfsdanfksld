"""Live PostgreSQL integration is opt-in and refuses non-test databases."""

import os
import subprocess
import sys
import uuid

import pytest
from flask_migrate import check, upgrade
from sqlalchemy.engine import make_url

from backend import create_app
from backend.config import ROOT
from backend.framework import services
from backend.framework.extension import framework
from backend.modules.auth.service import register_account
from database import db


def test_postgresql_schema_compiles_without_connecting():
    env = {
        **os.environ,
        "APP_ENV": "testing",
        "SECRET_KEY": "offline-test-key",
        "DATABASE_URL": "postgresql+psycopg://framework:unused@127.0.0.1/framework_test",
        "PUBLIC_BASE_URL": "http://localhost",
        "MAIL_TRANSPORT": "disabled",
    }
    env.pop("RENDER", None)
    result = subprocess.run(
        [sys.executable, "manage.py", "db", "upgrade", "--sql"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "BYTEA" in result.stdout and "SERIAL" in result.stdout and "CREATE TABLE pages" in result.stdout


@pytest.mark.postgres
def test_live_postgres_schema_resources_and_publishing():
    url = os.getenv("TEST_POSTGRES_URL", "")
    if not url:
        pytest.skip("TEST_POSTGRES_URL was not supplied; CI provides a disposable PostgreSQL service.")
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgres") or not (parsed.database or "").endswith("_test"):
        pytest.fail("Refusing a database that is not a disposable PostgreSQL *_test database.")
    app = create_app(
        {
            "APP_ENV": "testing",
            "TESTING": True,
            "SECRET_KEY": "postgres-test-only-key",
            "SQLALCHEMY_DATABASE_URI": url,
            "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
            "MAIL_TRANSPORT": "disabled",
            "RATELIMIT_ENABLED": False,
            "PUBLIC_BASE_URL": "http://localhost",
            "TRUSTED_HOSTS": ["localhost"],
            "SESSION_COOKIE_SECURE": False,
        }
    )
    suffix = uuid.uuid4().hex
    with app.app_context():
        upgrade(directory=str(ROOT / "database/migrations"))
        check(directory=str(ROOT / "database/migrations"))
        user = register_account("PG User", f"pg-{suffix}@example.com", "Postgres-password-42")
        resource = framework().resources["notes"]
        record = services.create(resource, user, {"title": "Postgres record", "body": "Real PostgreSQL transaction"})
        identifier = record.id
        assert services.update(resource, user, identifier, {"version": 1, "body": "Updated"}).version == 2
        services.delete(resource, user, identifier, 2)
        user.role = "admin"
        db.session.commit()
        page = services.create(
            framework().resources["pages"],
            user,
            {"title": "Published", "slug": "pg-" + suffix, "body": "From PostgreSQL", "published": True},
        )
        slug = page.slug
    assert b"From PostgreSQL" in app.test_client().get("/pages/" + slug).data
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
