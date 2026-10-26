"""BACKEND: authorization, safe redirects, and consistent browser protection."""

import logging
import time
import uuid
from functools import wraps
from urllib.parse import unquote, urlsplit

from flask import abort, current_app, g, request
from flask_login import current_user


def safe_next(value):
    if not value:
        return None
    decoded = unquote(value)
    try:
        parsed = urlsplit(decoded)
    except ValueError:
        return None
    if (
        parsed.scheme
        or parsed.netloc
        or not decoded.startswith("/")
        or decoded.startswith("//")
        or "\\" in decoded
        or any(ord(x) < 32 for x in decoded)
    ):
        return None
    return decoded


def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)

    return wrapped


def install_security(app):
    @app.before_request
    def trace_request():
        g.request_id = str(uuid.uuid4())
        g.started_at = time.monotonic()

    @app.after_request
    def headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:"
        )
        if current_app.config["APP_ENV"] == "production" and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        if request.endpoint != "health.live":
            current_app.logger.info(
                "request method=%s path=%s status=%s elapsed_ms=%s request_id=%s",
                request.method,
                request.url_rule.rule if request.url_rule else "<unmatched>",
                response.status_code,
                round(1000 * (time.monotonic() - getattr(g, "started_at", time.monotonic()))),
                getattr(g, "request_id", ""),
            )
        return response

    app.logger.setLevel(logging.INFO)
