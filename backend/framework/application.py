"""Production-oriented Flask factory: configuration, extensions, modules, and presentation."""

import importlib
import secrets
import sqlite3

from flask import Flask, g, jsonify, redirect, request, url_for
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

from backend.common.errors import install_errors
from backend.common.security import install_security
from backend.config import ROOT, configuration
from backend.extensions import csrf, limiter, login, migrate
from backend.module_registry import BLUEPRINT_MODULES, RESOURCE_MODULES
from database import db


@event.listens_for(Engine, "connect")
def sqlite_settings(connection, record):
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        for pragma in ["foreign_keys=ON", "busy_timeout=15000", "journal_mode=WAL"]:
            cursor.execute("PRAGMA " + pragma)
        cursor.close()


def create_application(overrides=None):
    app = Flask(
        "backend",
        template_folder=str(ROOT / "frontend/templates"),
        static_folder=str(ROOT / "frontend/static"),
        static_url_path="/static",
        instance_path=str(ROOT / "instance"),
    )
    app.config.update(configuration(overrides))
    app.config.setdefault("RESOURCE_MODULES", list(RESOURCE_MODULES))
    app.config["DUMMY_PASSWORD_HASH"] = generate_password_hash(
        secrets.token_urlsafe(24), method=app.config["PASSWORD_HASH_METHOD"]
    )
    for directory in ["database/data", "instance"]:
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    hops = app.config["PROXY_FIX_HOPS"]
    if hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)
    install_security(app)
    db.init_app(app)
    from database.models import User

    login.init_app(app)
    login.session_protection = "strong"
    login.login_view = login.refresh_view = "auth.login_page"
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db, directory=str(ROOT / "database/migrations"), render_as_batch=True, compare_type=True)

    @login.user_loader
    def load_user(identifier):
        try:
            user_id, version = map(int, identifier.split(":"))
        except (ValueError, AttributeError):
            return None
        user = db.session.get(User, user_id)
        return user if user and user.active and user.session_version == version else None

    @login.unauthorized_handler
    def unauthenticated():
        if request.path.startswith("/api/"):
            return jsonify(
                error={
                    "status": 401,
                    "message": "Please sign in.",
                    "fields": {},
                    "request_id": getattr(g, "request_id", ""),
                }
            ), 401
        return redirect(url_for("auth.login_page", next=request.full_path.rstrip("?")))

    for target in BLUEPRINT_MODULES:
        app.register_blueprint(importlib.import_module(target).bp)
    from backend.framework.extension import Framework, framework

    Framework(app)
    from backend.cli import register_commands

    register_commands(app)
    install_errors(app)

    @app.context_processor
    def shared_values():
        from backend.common.forms import ActionForm

        resources = [r for r in framework().resources.values() if r.policy.allows(current_user)]
        return {
            "app_name": app.config["APP_NAME"],
            "app_tagline": app.config["APP_TAGLINE"],
            "logout_form": ActionForm(),
            "navigation_resources": resources,
            "password_reset_enabled": app.config["MAIL_TRANSPORT"] != "disabled",
        }

    def page_url(page):
        args = dict(request.view_args or {})
        args.update(request.args.to_dict())
        args["page"] = page
        return url_for(request.endpoint, **args)

    app.jinja_env.globals.update(page_url=page_url, getattr=getattr)
    app.jinja_env.filters["date_label"] = lambda value: value.strftime("%d %b %Y") if value else "—"
    app.jinja_env.filters["field_value"] = lambda value: (
        "Yes" if value is True else "No" if value is False else "—" if value is None or value == "" else str(value)
    )
    return app
