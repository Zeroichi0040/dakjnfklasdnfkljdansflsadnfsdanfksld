"""Production entry point for Gunicorn, PythonAnywhere, and other WSGI hosts."""

import os

os.environ.setdefault("APP_ENV", "production")
from backend import create_app  # noqa: E402

app = create_app()
application = app
