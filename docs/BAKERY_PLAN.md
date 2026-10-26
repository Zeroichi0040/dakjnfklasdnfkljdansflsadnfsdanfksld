# Bakery implementation plan and repository assessment

The existing app is a modular Flask factory with Flask-Login, Flask-WTF/CSRF,
Flask-Limiter, SQLAlchemy, Alembic, Waitress and pytest. It uses server-rendered
Jinja templates and local CSS/JavaScript; no frontend build is needed. Users have
member/admin roles, revocable sessions and hashed passwords. Contact inquiries,
private files, notes, publishing and account administration are reusable features.
The module registry composes blueprints; the model registry supplies migration
metadata. Existing readiness checks require migration HEAD, not just connectivity.

Milestones:
1. Inspect all directories, models, migrations, routes, templates, CI and guides;
   run the existing suite as a baseline.
2. Add bakery models, reviewed migration, stock/payment/order services and seed CLI.
3. Build landing, searchable catalogue, cart, checkout, receipts and customer history.
4. Add protected product editing, order transitions and database sales summaries.
5. Exercise existing and new tests, real HTTP workflows, migration repeatability,
   accessibility/responsiveness and document implementation and Windows setup.

Decisions: reuse auth/ORM; keep framework modules accessible; custom bakery routes
rather than generated CRUD for multi-table transactions. Decimal money, immutable
order-item snapshots, database constraints, serialized mutations and conditional
stock updates protect purchases. Reserve at checkout; restore once on cancellation
or failed simulation. Checkout tokens prevent replay duplication. All payment data
is synthetic. Local original SVG illustrations avoid third-party image requests.

Constraints: SQLite is suitable for this educational single-instance app; checkout
writes serialize on the existing site_state row (PostgreSQL uses a row lock). No
shipping, real gateway, tax engine or production deployment is part of this work.
Windows launchers remain supported; this machine can validate Linux only. Existing
protected setup restrictions apply to onboarding, not this explicitly authorized
application implementation. No new runtime dependency is needed.
