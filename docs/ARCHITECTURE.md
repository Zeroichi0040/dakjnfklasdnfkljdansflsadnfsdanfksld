# Architecture

| Layer | Location | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/templates`, `frontend/static` | Server-rendered HTML, reusable components, styles, browser API calls |
| Application composition | `backend/module_registry.py` | Enabled blueprints and resources |
| Framework extension | `backend/framework/extension.py` | Application-local resource registry and generated blueprint registration |
| Public resource API | `backend/framework/definitions.py` | `Resource`, `Field`, field contracts |
| Access policies | `backend/framework/policies.py` | Consistent owner/admin scopes for reads, writes and exports |
| Validation/forms | `backend/framework/validation.py`, `forms.py` | One value contract and generated Flask-WTF forms |
| Business transactions | `backend/framework/services.py` | Owner queries, mutations, hooks, audit events, version checks |
| HTTP adapters | `backend/framework/routes.py` | HTML and JSON endpoints over the same services |
| API discovery | `backend/framework/openapi.py` | OpenAPI generated from the actual enabled resources |
| Your feature | `backend/modules/<feature>` | Resource definition and domain hooks; optional custom Flask routes |
| Persistence | `database/models`, `database/migrations` | SQLAlchemy tables, reviewed Alembic revisions |
| Private runtime | `database/data`, `database/backups`, `instance` | SQLite, consistent backups, private development mail/settings |

## One full request

1. The browser submits a resource form or sends a JSON request.
2. Flask validates the session, CSRF token, rate limit, and resource policy.
3. The shared service validates declared fields and selects a record within the
   policy's scope. Owner IDs come from the authenticated account, not input fields.
4. A write runs your optional hook, updates the model and audit event, and commits
   one database transaction. Failures roll it back. Version checks prevent silent
   overwrites from stale tabs; SQLAlchemy also checks versions at the SQL layer.
5. HTML requests redirect to a rendered record; JSON requests receive serialized data.
   The browser's Refresh action reads the actual JSON endpoint using the same session.

`backend.create_app()` delegates to the framework factory. Extension instances are
unbound until `init_app`; each app has its own registry. Importing the factory does
not create tables or seed users. Setup and deployment apply committed migrations.

## Included modules

Accounts/authentication, profile/password settings, dashboard/activity, private
images, administrator account/message management, public contact/privacy pages,
Notes (owner resource), and Website pages (administrator resource). Public page
URLs select only records explicitly marked published. Drafts stay private.

Add a custom blueprint to `BLUEPRINT_MODULES` for non-CRUD workflows. Add a resource
to `RESOURCE_MODULES` for generated HTML/API CRUD. Neither requires modifying the
engine. The resource generator performs the latter registration automatically.
