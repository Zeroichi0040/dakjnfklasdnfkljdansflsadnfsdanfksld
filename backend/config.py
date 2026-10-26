"""BACKEND: environment settings. All filesystem paths are project-relative."""

import os
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def boolean(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def configuration(overrides=None):
    load_dotenv(ROOT / ".env", override=False)
    env = os.getenv("APP_ENV", "development")
    values = {
        "APP_ENV": env,
        "TESTING": False,
        "DEBUG": False,
        "APP_NAME": os.getenv("APP_NAME", "Mithi Bakehouse"),
        "APP_TAGLINE": os.getenv("APP_TAGLINE", "Small batches. Everyday joys."),
        "SECRET_KEY": os.getenv("SECRET_KEY", ""),
        "PUBLIC_BASE_URL": os.getenv("PUBLIC_BASE_URL", ""),
        "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", ""),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "hide_parameters": True},
        "PASSWORD_HASH_METHOD": "scrypt",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        # Static/parallel reads must not overwrite a newer basket or checkout token cookie.
        "SESSION_REFRESH_EACH_REQUEST": False,
        "SESSION_COOKIE_SECURE": boolean("SESSION_COOKIE_SECURE", env == "production"),
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=8),
        "REMEMBER_COOKIE_HTTPONLY": True,
        "REMEMBER_COOKIE_SECURE": env == "production",
        "MAX_CONTENT_LENGTH": 3 * 1024 * 1024,
        "MAX_FORM_MEMORY_SIZE": 128 * 1024,
        "MAX_FORM_PARTS": 40,
        "MAX_IMAGE_BYTES": 2 * 1024 * 1024,
        "USER_FILE_QUOTA": 20 * 1024 * 1024,
        "WTF_CSRF_TIME_LIMIT": 7200,
        "RATELIMIT_STORAGE_URI": os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        "RATELIMIT_HEADERS_ENABLED": True,
        "RATELIMIT_ENABLED": True,
        "MAIL_TRANSPORT": os.getenv("MAIL_TRANSPORT", "disabled" if env == "production" else "outbox"),
        "MAIL_SERVER": os.getenv("MAIL_SERVER", ""),
        "MAIL_PORT": int(os.getenv("MAIL_PORT", "587")),
        "MAIL_USERNAME": os.getenv("MAIL_USERNAME", ""),
        "MAIL_PASSWORD": os.getenv("MAIL_PASSWORD", ""),
        "MAIL_FROM": os.getenv("MAIL_FROM", ""),
        "MAIL_USE_TLS": boolean("MAIL_USE_TLS", True),
        "PROXY_FIX_HOPS": int(os.getenv("PROXY_FIX_HOPS", "0")),
        "SIGNUP_ENABLED": boolean("SIGNUP_ENABLED", True),
        "RESET_TOKEN_MAX_AGE": 1800,
    }
    if overrides:
        values.update(overrides)
    env = values["APP_ENV"]
    if env not in {"development", "testing", "production"}:
        raise ValueError("APP_ENV must be development, testing, or production.")
    if not values["SQLALCHEMY_DATABASE_URI"]:
        values["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + (ROOT / "database/data/application.sqlite3").as_posix()
    uri = values["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("postgres://"):
        uri = "postgresql+psycopg://" + uri[len("postgres://") :]
    elif uri.startswith("postgresql://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql://") :]
    values["SQLALCHEMY_DATABASE_URI"] = uri
    if not uri.startswith(("sqlite:", "postgresql+psycopg:")):
        raise ValueError("Use SQLite or a PostgreSQL DATABASE_URL.")
    if uri.startswith("sqlite:"):
        values["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] = {"timeout": 15}
    else:
        values["SQLALCHEMY_ENGINE_OPTIONS"].update(pool_size=3, max_overflow=2, pool_recycle=300)
    if not values["PUBLIC_BASE_URL"]:
        host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
        values["PUBLIC_BASE_URL"] = "https://" + host if host else "http://127.0.0.1:5000"
    parsed = urlsplit(values["PUBLIC_BASE_URL"])
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.path not in {"", "/"}
        or parsed.username is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("PUBLIC_BASE_URL must be the site's http(s) origin, without a path or credentials.")
    values["PUBLIC_BASE_URL"] = values["PUBLIC_BASE_URL"].rstrip("/")
    trusted = os.getenv("TRUSTED_HOSTS", "").strip()
    values["TRUSTED_HOSTS"] = values.get("TRUSTED_HOSTS") or (
        [x.strip() for x in trusted.split(",") if x.strip()] if trusted else [parsed.hostname, "localhost", "127.0.0.1"]
    )
    if not 0 <= values["PROXY_FIX_HOPS"] <= 2:
        raise ValueError("PROXY_FIX_HOPS must be 0, 1, or 2 and match your trusted reverse proxy.")
    if env == "production":
        if len(values["SECRET_KEY"]) < 32 or values["SECRET_KEY"].startswith(("change-", "replace-")):
            raise ValueError("Production requires a unique SECRET_KEY of at least 32 characters.")
        local = parsed.hostname in {"localhost", "127.0.0.1"}
        if not local and (parsed.scheme != "https" or not values["SESSION_COOKIE_SECURE"]):
            raise ValueError("Public production deployments require HTTPS and SESSION_COOKIE_SECURE=true.")
        if values["MAIL_TRANSPORT"] == "outbox":
            raise ValueError("The development outbox cannot deliver production email. Select smtp or disabled.")
        if os.getenv("RENDER") and uri.startswith("sqlite:"):
            raise ValueError("Render's filesystem is ephemeral. Set DATABASE_URL to persistent PostgreSQL.")
        if not trusted:
            values["TRUSTED_HOSTS"] = [parsed.hostname]
    if not values["SECRET_KEY"]:
        private = ROOT / "instance"
        private.mkdir(parents=True, exist_ok=True)
        key = private / ".secret_key"
        try:
            with key.open("x", encoding="utf-8") as stream:
                stream.write(secrets.token_hex(32))
            key.chmod(0o600)
        except FileExistsError:
            pass
        values["SECRET_KEY"] = key.read_text(encoding="utf-8").strip()
    if values["MAIL_TRANSPORT"] not in {"disabled", "outbox", "smtp"}:
        raise ValueError("MAIL_TRANSPORT must be disabled, outbox, or smtp.")
    if values["MAIL_TRANSPORT"] == "smtp" and not all(values[x] for x in ["MAIL_SERVER", "MAIL_FROM"]):
        raise ValueError("SMTP requires MAIL_SERVER and MAIL_FROM.")
    return values
