import os
import shutil
import sqlite3
import subprocess
import sys

import pytest
from flask_migrate import check, upgrade
from sqlalchemy import inspect

from backend import create_app
from backend.config import ROOT, configuration
from backend.framework import Field, Resource
from backend.framework.extension import framework
from database import db
from database.models.note import Note
from scripts.scaffold import scaffold
from tests.conftest import PASSWORD, login, post_form


def test_pages_headers_and_protected_source(client, users):
    for path in ["/", "/contact", "/privacy", "/auth/login", "/auth/register", "/api/docs", "/api/openapi.json"]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]
        assert response.headers["Cache-Control"] == "no-store"
    for path in ["/.env", "/database/data/application.sqlite3", "/backend/config.py", "/instance/.secret_key"]:
        assert client.get(path).status_code == 404
    assert client.get("/", headers={"Host": "untrusted.example"}).status_code == 400
    assert client.get("/api/v1/notes").status_code == 401
    assert client.get("/app").status_code == 302
    login(client)
    for path in [
        "/app",
        "/app/activity",
        "/app/notes",
        "/app/notes/new",
        "/files",
        "/account/profile",
        "/account/password",
    ]:
        assert client.get(path).status_code == 200, path


def test_migrations_and_multiple_app_instances(app):
    with app.app_context():
        upgrade(directory=str(ROOT / "database/migrations"))
        check(directory=str(ROOT / "database/migrations"))
        names = set(inspect(db.engine).get_table_names())
        assert {"users", "notes", "pages", "attachments", "audit_events", "inquiries", "site_state"} <= names
        original = framework()
    second = create_app(dict(app.config))
    with second.app_context():
        assert framework() is not original
        assert set(framework().resources) == {"notes", "pages"}
        db.engine.dispose()
    assert app.test_client().get("/health/ready").status_code == 200


def test_extension_contract_rejects_bad_definitions(app):
    with pytest.raises(ValueError):
        Field("id", "ID")
    with pytest.raises(ValueError):
        Field("value", "Value", kind="unknown")
    with pytest.raises(ValueError):
        Resource("notes", "Notes", "Note", Note, (Field("missing", "Missing"),))
    with app.app_context(), pytest.raises(ValueError):
        framework().register(app, framework().resources["notes"])


def test_production_guards(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    base = {
        "APP_ENV": "production",
        "SECRET_KEY": "x" * 64,
        "PUBLIC_BASE_URL": "https://app.example",
        "SESSION_COOKIE_SECURE": True,
        "MAIL_TRANSPORT": "disabled",
    }
    for changes in [
        {"SECRET_KEY": ""},
        {"SESSION_COOKIE_SECURE": False},
        {"PUBLIC_BASE_URL": "http://app.example"},
        {"MAIL_TRANSPORT": "outbox"},
    ]:
        with pytest.raises(ValueError):
            configuration({**base, **changes})
    result = configuration({**base, "SQLALCHEMY_DATABASE_URI": "postgresql://test:test@localhost/application_test"})
    assert result["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://")
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(ValueError, match="ephemeral"):
        configuration(base)


def test_production_cookie_and_hsts(app):
    settings = dict(app.config)
    settings.update(
        APP_ENV="production",
        PUBLIC_BASE_URL="https://localhost",
        MAIL_TRANSPORT="disabled",
        SESSION_COOKIE_SECURE=True,
        TRUSTED_HOSTS=["localhost"],
    )
    production = create_app(settings)
    result = production.test_client().get("/api/v1/csrf", base_url="https://localhost")
    assert "Secure" in result.headers["Set-Cookie"] and "HttpOnly" in result.headers["Set-Cookie"]
    assert result.headers["Strict-Transport-Security"] == "max-age=31536000"


def test_owner_commands_and_consistent_backup(app, tmp_path):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "--email", "newowner@example.com", "--name", "Owner"],
        input=PASSWORD + "\n" + PASSWORD + "\n",
    )
    assert result.exit_code == 0, result.output
    assert "notes" in runner.invoke(args=["resources"]).output
    assert runner.invoke(args=["check"]).exit_code == 0
    backup = tmp_path / "backup.sqlite3"
    assert runner.invoke(args=["backup-db", "--output", str(backup)]).exit_code == 0
    assert runner.invoke(args=["backup-db", "--output", str(backup)]).exit_code != 0
    with sqlite3.connect(backup) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 1


def test_error_response_does_not_depend_on_database_user_context(app, client, users, monkeypatch):
    login(client)

    def unavailable(identifier):
        raise RuntimeError("Private database failure details")

    monkeypatch.setattr(app.login_manager, "_user_callback", unavailable)
    result = client.get("/app")
    assert result.status_code == 500 and b"Private database failure" not in result.data
    result = client.get("/api/v1/me")
    assert result.status_code == 500 and "error" in result.json


def test_rate_limiting_remains_active(app):
    from backend.extensions import limiter

    settings = dict(app.config)
    settings["RATELIMIT_ENABLED"] = True
    limited = create_app(settings)
    with limited.app_context():
        limiter.reset()
    client = limited.test_client()
    for _ in range(5):
        assert (
            post_form(
                client, "/contact", name="Visitor", email="visitor@example.com", message="Legitimate test message."
            ).status_code
            == 303
        )
    assert (
        post_form(
            client, "/contact", name="Visitor", email="visitor@example.com", message="One more test message."
        ).status_code
        == 429
    )


def copy_source(destination):
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".env", "*.sqlite3*", ".secret_key", "outbox"
        ),
    )


@pytest.mark.parametrize(
    "name,fields",
    [
        ("../escape", ()),
        ("notes", ()),
        ("class", ()),
        ("auth", ()),
        ("AName", ()),
        ("a", ()),
        ("products", ("id:text",)),
        ("products", ("name:text", "name:integer")),
        ("products", ("price:unknown",)),
    ],
)
def test_generator_rejects_unsafe_inputs(tmp_path, name, fields):
    root = tmp_path / "project"
    copy_source(root)
    before = (root / "backend/module_registry.py").read_bytes()
    with pytest.raises(ValueError):
        scaffold(root, name, fields)
    assert (root / "backend/module_registry.py").read_bytes() == before


def test_generated_resource_is_a_working_full_vertical_slice(tmp_path):
    root = tmp_path / "generated_application"
    copy_source(root)
    scaffold(root, "products", ("name:text", "price:decimal", "stock:integer", "available:boolean", "launch_date:date"))
    env = {
        **os.environ,
        "APP_ENV": "testing",
        "SECRET_KEY": "generated-test-key",
        "DATABASE_URL": "sqlite:///" + (tmp_path / "generated.sqlite3").as_posix(),
        "PUBLIC_BASE_URL": "http://localhost",
        "TRUSTED_HOSTS": "localhost",
        "PROXY_FIX_HOPS": "0",
        "MAIL_TRANSPORT": "disabled",
        "SESSION_COOKIE_SECURE": "false",
    }
    env.pop("RENDER", None)
    for cmd in [
        ["manage.py", "db", "upgrade"],
        ["manage.py", "db", "migrate", "-m", "Add products"],
        ["manage.py", "db", "upgrade"],
        ["manage.py", "db", "check"],
    ]:
        result = subprocess.run([sys.executable, *cmd], cwd=root, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
    script = """
from backend import create_app
from backend.modules.auth.service import register_account
app=create_app({'PASSWORD_HASH_METHOD':'pbkdf2:sha256:1000','RATELIMIT_ENABLED':False})
with app.app_context():
    register_account('One','one@example.com','Test-password-42')
    register_account('Two','two@example.com','Test-password-42')
c=app.test_client()
def request(method,path,data):
    token=c.get('/api/v1/csrf').json['csrf_token']
    return c.open(path,method=method,json=data,headers={'X-CSRFToken':token})
def sign_in(email):
    assert request('POST','/api/v1/auth/login',{'email':email,'password':'Test-password-42'}).status_code==200
sign_in('one@example.com')
assert b'Products' in c.get('/app').data
assert '/api/v1/products' in c.get('/api/openapi.json').json['paths']
data={'name':'Camera','price':'199.95','stock':2,'available':True,'launch_date':'2026-11-01'}
r=request('POST','/api/v1/products',data)
assert r.status_code==201,r.get_data(as_text=True)
record=r.json['data'];identifier=record['id']
assert record['price']=='199.95' and record['stock']==2 and record['available'] is True
assert c.get('/app/products').status_code==200
assert b'199.95' in c.get('/app/products').data
assert c.get(f'/app/products/{identifier}').status_code==200
assert request('PATCH',f'/api/v1/products/{identifier}',{'version':1,'price':'249.00'}).json['data']['version']==2
token=c.get('/api/v1/csrf').json['csrf_token']
assert c.post(f'/app/products/{identifier}/edit',data={'csrf_token':token,'version':2,'name':'Camera Pro','price':'299.00','stock':'3','available':'y','launch_date':'2026-12-01'}).status_code==303
assert c.get(f'/api/v1/products/{identifier}').json['data']['name']=='Camera Pro'
assert b'Camera Pro' in c.get('/app/products/export.csv').data
assert request('POST','/api/v1/auth/logout',{}).status_code==204
sign_in('two@example.com')
assert c.get('/api/v1/products').json['data']==[]
assert c.get(f'/api/v1/products/{identifier}').status_code==404
request('POST','/api/v1/auth/logout',{})
sign_in('one@example.com')
assert request('DELETE',f'/api/v1/products/{identifier}',{'version':3}).status_code==204
assert c.get(f'/api/v1/products/{identifier}').status_code==404
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_resource_products.py"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
