# Dependencies

Direct runtime dependencies are pinned in `requirements.txt`. They are free software
with their respective upstream licenses. Optional test/lint/audit tools are in
`requirements-dev.txt`. A package install does not subscribe you to a cloud service.

| Dependency | Purpose |
| --- | --- |
| Flask, Werkzeug, Jinja2, itsdangerous | HTTP routing, templates, HTTP tools, signed tokens |
| Flask-SQLAlchemy, SQLAlchemy | Models, queries and transactions |
| Flask-Migrate, Alembic | Versioned schema migrations |
| Flask-Login | Account sessions |
| Flask-WTF, WTForms, email-validator | Forms, CSRF and email syntax checks |
| Flask-Limiter | Request limits |
| python-dotenv | Private environment settings |
| Waitress, Gunicorn | Cross-platform local and Linux production WSGI servers |
| psycopg | PostgreSQL driver |
| Pillow | Private image verification |
| pytest, Ruff, pip-audit | Optional verification tooling |

The frontend uses local assets, system fonts and an included SVG icon. It has no
CDN, analytics SDK, licensed stock photograph or paid API dependency. Installed
packages include their own license metadata and transitive dependencies.
