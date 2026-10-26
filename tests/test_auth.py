from pathlib import Path

import pytest

from backend.modules.auth import service
from database import db
from database.models import User
from database.models.note import Note
from tests.conftest import PASSWORD, api_request, csrf, login, post_form


def test_registration_normalizes_email_and_cannot_choose_admin(client, app):
    response = post_form(
        client,
        "/auth/register",
        display_name=" New Student ",
        email="NEW@EXAMPLE.COM",
        password=PASSWORD,
        confirm=PASSWORD,
        role="admin",
    )
    assert response.status_code == 303
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == "new@example.com"))
        assert user.role == "member" and user.display_name == "New Student"
        assert user.password_hash != PASSWORD and user.check_password(PASSWORD)
        assert db.session.scalar(db.select(db.func.count(Note.id)).where(Note.user_id == user.id)) == 0


def test_duplicate_signup_and_bad_password_are_rejected(client, app, users):
    response = post_form(
        client, "/auth/register", display_name="Other", email="ADA@example.com", password=PASSWORD, confirm=PASSWORD
    )
    assert response.status_code == 422
    response = post_form(
        client, "/auth/register", display_name="Other", email="new@example.com", password="short", confirm="short"
    )
    assert response.status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(User.id))) == 3


def test_csrf_is_required_on_html_and_json(client, users):
    assert client.post("/auth/login", data={"email": "ada@example.com", "password": PASSWORD}).status_code == 400
    response = client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert response.status_code == 400 and "error" in response.json


def test_api_session_rotates_token_and_logout_is_post_only(client, users):
    old = csrf(client)
    new = login(client)
    assert new != old
    assert client.get("/api/v1/me").json["email"] == "ada@example.com"
    assert client.get("/auth/logout").status_code == 405
    stale = client.post("/api/v1/auth/logout", headers={"X-CSRFToken": old})
    assert stale.status_code == 400
    assert api_request(client, "POST", "/api/v1/auth/logout", {}).status_code == 204
    assert client.get("/api/v1/me").status_code == 401


@pytest.mark.parametrize(
    "next_url", ["https://evil.example/", "//evil.example", "/\\evil.example", "%2F%2Fevil.example", "/%0aevil"]
)
def test_login_does_not_redirect_outside_site(client, users, next_url):
    response = client.post(
        "/auth/login",
        query_string={"next": next_url},
        data={"csrf_token": csrf(client), "email": "ada@example.com", "password": PASSWORD},
    )
    assert response.status_code == 303 and response.headers["Location"] == "/app"


def test_local_next_path_is_preserved(client, users):
    response = client.post(
        "/auth/login?next=/account/profile",
        data={"csrf_token": csrf(client), "email": "ada@example.com", "password": PASSWORD},
    )
    assert response.headers["Location"] == "/account/profile"


def test_password_change_revokes_other_sessions(app, client, users):
    other = app.test_client()
    login(client)
    login(other)
    new_password = "Replacement-password-2026"
    response = post_form(
        client, "/account/password", current_password=PASSWORD, password=new_password, confirm=new_password
    )
    assert response.status_code == 303
    assert client.get("/api/v1/me").status_code == 200
    assert other.get("/api/v1/me").status_code == 401
    with app.app_context():
        assert service.authenticate("ada@example.com", PASSWORD) is None
        assert service.authenticate("ada@example.com", new_password)


def test_reset_link_single_use_and_private_outbox(app, client, users):
    response = post_form(client, "/auth/forgot", email="ada@example.com")
    assert response.status_code == 303
    messages = list((Path(app.instance_path) / "outbox").glob("*.eml"))
    assert len(messages) == 1
    text = messages[0].read_text()
    assert "http://localhost/auth/reset/" in text
    # Extract from the original service token to avoid MIME line-folding assumptions.
    with app.app_context():
        token = service.reset_token(db.session.get(User, users["ada"]))
    assert client.get("/auth/reset/" + token).status_code == 200
    new_password = "Reset-password-valid-2026"
    assert post_form(client, "/auth/reset/" + token, password=new_password, confirm=new_password).status_code == 303
    assert client.get("/auth/reset/" + token).status_code == 400
    assert client.get("/instance/outbox/" + messages[0].name).status_code == 404


def test_reset_expiry_tamper_and_disabled_mail(app, client, users):
    with app.app_context():
        token = service.reset_token(db.session.get(User, users["ada"]))
        app.config["RESET_TOKEN_MAX_AGE"] = -1
        assert service.token_user(token) is None
        assert service.token_user(token + "broken") is None
    app.config["MAIL_TRANSPORT"] = "disabled"
    assert client.get("/auth/forgot").status_code == 503
    assert b"Request password reset" not in client.get("/auth/login").data


def test_profile_and_closed_registration(client, app, users):
    login(client)
    response = post_form(client, "/account/profile", display_name="A new name", role="admin")
    assert response.status_code == 303
    assert client.get("/api/v1/me").json["display_name"] == "A new name"
    assert client.get("/api/v1/me").json["role"] == "member"
    app.config["SIGNUP_ENABLED"] = False
    assert app.test_client().get("/auth/register").status_code == 403


def test_inactive_account_cannot_authenticate(app, client, users):
    with app.app_context():
        db.session.get(User, users["ada"]).active = False
        db.session.commit()
    response = api_request(client, "POST", "/api/v1/auth/login", {"email": "ada@example.com", "password": PASSWORD})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body", [[], "wrong", {"email": [], "password": []}, {"email": "ada@example.com", "password": 42}]
)
def test_malformed_login_returns_client_error(client, body):
    assert api_request(client, "POST", "/api/v1/auth/login", body).status_code == 422
