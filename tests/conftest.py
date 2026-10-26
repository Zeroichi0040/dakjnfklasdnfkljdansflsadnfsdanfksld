import pytest
from flask_migrate import upgrade

from backend import create_app
from backend.config import ROOT
from backend.modules.auth.service import register_account
from database import db

PASSWORD = "Student-test-password-42"


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Host credentials must never redirect these tests to a real database.
    for name in ("DATABASE_URL", "RENDER", "TRUSTED_HOSTS", "PROXY_FIX_HOPS"):
        monkeypatch.delenv(name, raising=False)
    application = create_app(
        {
            "APP_ENV": "testing",
            "TESTING": True,
            "SECRET_KEY": "tests-only-unique-key-that-is-never-used-in-production",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (tmp_path / "isolated.sqlite3").as_posix(),
            "PUBLIC_BASE_URL": "http://localhost",
            "TRUSTED_HOSTS": ["localhost", "127.0.0.1"],
            "SESSION_COOKIE_SECURE": False,
            "PROXY_FIX_HOPS": 0,
            "RATELIMIT_ENABLED": False,
            "WTF_CSRF_ENABLED": True,
            "SIGNUP_ENABLED": True,
            "MAIL_TRANSPORT": "outbox",
            "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
        }
    )
    application.instance_path = str(tmp_path / "instance")
    with application.app_context():
        upgrade(directory=str(ROOT / "database/migrations"))
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def users(app):
    with app.app_context():
        first = register_account("Ada Student", "ada@example.com", PASSWORD)
        second = register_account("Grace Student", "grace@example.com", PASSWORD)
        admin = register_account("Site Owner", "owner@example.com", PASSWORD)
        admin.role = "admin"
        db.session.commit()
        return {"ada": first.id, "grace": second.id, "admin": admin.id}


def csrf(client):
    response = client.get("/api/v1/csrf")
    assert response.status_code == 200
    return response.json["csrf_token"]


def login(client, email="ada@example.com", password=PASSWORD):
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}, headers={"X-CSRFToken": csrf(client)}
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.json["csrf_token"]


def post_form(client, path, **values):
    return client.post(path, data={"csrf_token": csrf(client), **values})


def api_request(client, method, path, body):
    return client.open(path, method=method, json=body, headers={"X-CSRFToken": csrf(client)})
