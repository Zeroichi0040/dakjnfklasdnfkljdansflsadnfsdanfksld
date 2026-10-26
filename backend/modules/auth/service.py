"""BACKEND: account rules shared by browser pages and the JSON API."""

import hashlib
import secrets

from flask import current_app, g, session, url_for
from flask_login import login_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash

from backend.common.errors import ValidationError
from backend.integrations.email import send_message
from database import db
from database.models import AuditEvent, User
from database.repositories import user_by_email


def start_session(user):
    # Keep only a validated anonymous basket across session rotation, never authentication state.
    from backend.modules.bakery.service import BakeryError, normalize_cart

    try:
        cart = normalize_cart(session.get("bakery_cart", {}))
    except BakeryError:
        cart = {}
    session.clear()
    if cart:
        session["bakery_cart"] = cart
    g.pop("csrf_token", None)
    login_user(user, remember=False, fresh=True)
    session.permanent = True


def register_account(display_name, email, password):
    name, email = display_name.strip(), email.strip().casefold()
    if not 1 <= len(name) <= 80 or not 12 <= len(password) <= 128:
        raise ValidationError({"account": ["Use a name of 1-80 characters and a password of 12-128 characters."]})
    if user_by_email(email):
        raise ValidationError({"email": ["This email cannot be used. Sign in or request a password reset."]})
    user = User(display_name=name, email=email, role="member")
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(AuditEvent(user_id=user.id, action="account.created", subject="Account created"))
    db.session.commit()
    return user


def authenticate(email, password):
    user = user_by_email(email)
    if user is None:
        check_password_hash(current_app.config["DUMMY_PASSWORD_HASH"], password)
        return None
    return user if user.active and user.check_password(password) else None


def reset_token(user):
    fingerprint = hashlib.sha256(user.password_hash.encode()).hexdigest()
    return URLSafeTimedSerializer(current_app.secret_key).dumps(
        {"id": user.id, "version": user.session_version, "fingerprint": fingerprint}, salt="password-reset"
    )


def token_user(token):
    try:
        payload = URLSafeTimedSerializer(current_app.secret_key).loads(
            token, salt="password-reset", max_age=current_app.config["RESET_TOKEN_MAX_AGE"]
        )
        user = db.session.get(User, int(payload["id"]))
        if not user or not user.active or user.session_version != payload["version"]:
            return None
        actual = hashlib.sha256(user.password_hash.encode()).hexdigest()
        return user if secrets.compare_digest(actual, payload["fingerprint"]) else None
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None


def request_reset(email):
    user = user_by_email(email)
    if user and user.active:
        url = current_app.config["PUBLIC_BASE_URL"] + url_for("auth.reset_password", token=reset_token(user))
        send_message(
            user.email,
            "Reset your password",
            f"Use this link within 30 minutes:\n\n{url}\n\nIf you did not request this, ignore this message.",
        )


def change_password(user, password):
    if not 12 <= len(password) <= 128:
        raise ValidationError({"password": ["Use between 12 and 128 characters."]})
    user.set_password(password)
    user.session_version += 1
    db.session.add(
        AuditEvent(
            user_id=user.id, action="account.password_changed", subject="Password changed; previous sessions revoked"
        )
    )
    db.session.commit()
