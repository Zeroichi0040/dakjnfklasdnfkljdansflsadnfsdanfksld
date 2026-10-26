# Mithi Bakehouse — Flask bakery ordering application

**Small batches. Everyday joys.** A functional, educational bakery built on the
existing Flask Fullstack Framework. Browse a database-backed catalogue, keep a
basket, place pickup orders, simulate payments, and manage orders, stock and sales.
Prices use Philippine pesos (₱). This reference application never charges money or
collects card numbers, CVVs, GCash PINs or other financial credentials.

## Start on Windows

Install Python 3.12 or 3.13 (supported: 3.11–3.14), then open PowerShell in this
repository. No Node, Redis, cloud account or paid service is needed.

```powershell
.\SETUP_WINDOWS.bat
.\START_WEBSITE.bat
```

Alternatively, use explicit interpreter commands:

```powershell
py -3.13 scripts\bootstrap.py --dev
.venv\Scripts\python.exe run.py --no-browser
```

Open http://127.0.0.1:5000 locally. Setup installs pinned requirements, creates
private local settings, applies migrations and seeds 12 sample products in five
categories. Repeating setup preserves settings, accounts, orders and inventory;
seeding only inserts missing product names. One sample cinnamon roll starts sold
out so the unavailable state is easy to demonstrate. Do not delete your database
to update the app: rerun setup or apply `python manage.py db upgrade`.

## Linux / macOS

```sh
python3 scripts/bootstrap.py --dev
.venv/bin/python run.py --no-browser
```

If upgrading an existing development environment, apply the new migration and seed:

```sh
python manage.py db upgrade
python manage.py bakery seed
python manage.py check
```

Use the virtual environment's Python (activate it or supply its path). Production
setup deliberately does not migrate or seed automatically; this project has not
been deployed as a production bakery.

## Administrator and demo

Create your own administrator; there are no default accounts or shared passwords:

```powershell
.venv\Scripts\python.exe manage.py create-admin
```

On Linux/macOS use `.venv/bin/python manage.py create-admin`. The command prompts
privately. Customers register through `/auth/register`. A public form cannot select
an administrator role. The sample catalogue contains no user or payment secrets.

- Storefront: `/`, `/products`, `/products/<id>`, `/cart`, `/checkout`.
- Customer: `/app`, `/orders`, `/orders/<id>`, profile/password settings.
- Bakery administration: `/admin/bakery`, `/admin/bakery/orders`, `/admin/bakery/products`.
- Existing contact, inquiries, account administration, notes, files and public page
  publishing remain available through navigation.

At checkout choose GCash/card simulation and a success, declined, insufficient or
cancelled scenario. Cash on pickup reserves stock but remains unpaid; use the
successful scenario for that method. A ready cash order requires simulated cash
collection before completion. Failed/cancelled orders restore stock once; paid
cancellations are marked as simulated refunds. Customers may cancel pending orders.

## Test and study

```sh
python -m pytest -q
python -m ruff check .
python manage.py db check
```

Tests use disposable databases, not live order data. The live PostgreSQL test is
optional and requires a disposable `TEST_POSTGRES_URL` ending in `_test`.

- [Implementation study](docs/IMPLEMENTATION_STUDY.md): data flow, transactions,
  security, tradeoffs, alternatives, concrete code and tests.
- [Feature map](docs/FEATURE_MAP.md): routes → templates → services → models → tests.
- [Demonstration checklist](docs/BAKERY_DEMO.md): complete customer/admin scenarios.
- [Implementation plan](docs/BAKERY_PLAN.md) and [verification](docs/BAKERY_VALIDATION.md).
- [Local asset attribution](docs/BAKERY_ASSETS.md).

Limitations: pickup only, simulated payment/refund/collection, no real gateway or
email delivery by default, no delivery/tax engine, reservation expiry, revenue
recognition ledger or production load testing. The cart is a signed browser session,
not a cross-device database cart. Inventory writes serialize for correctness rather
than high throughput. Windows launchers are preserved; local validation here ran
on Linux. Existing user branding is preserved; new installs default to Mithi.

---

# Original framework reference

# Flask Fullstack Framework

A reusable application framework built on **Flask**, with a real Python backend,
SQL database, server-rendered frontend, and browser JavaScript client.

The framework is `backend/framework/`. Your application modules are in
`backend/modules/`. Declare a resource once: the framework creates its forms,
HTML CRUD pages, JSON CRUD API, authorization, validation, pagination, search,
CSV export, navigation, transactions, version checks, and OpenAPI documentation.

## Open it

Extract the ZIP into a new folder and open **OPEN_ME_FIRST.html**.

| System | First setup | Start |
| --- | --- | --- |
| Windows PowerShell | `.\SETUP_WINDOWS.bat` | `.\START_WEBSITE.bat` |
| macOS / Linux | `bash setup.sh` | `bash start.sh` |

Use Python **3.12 or 3.13**. Supported range: 3.11–3.14. If Windows says the runtime
is missing, run `py install 3.13`, then retry setup. Alternatively, run
`py -3.13 scripts\bootstrap.py` directly. First installation needs internet.

Open **http://127.0.0.1:5000**. Create your own account; none is preinstalled.
Stop with Ctrl+C. The local launcher uses Waitress, with debug mode off.

## What is included

| Layer | Working capability |
| --- | --- |
| Frontend | Responsive layouts, reusable components, forms, tables, detail views, mobile navigation, and a JavaScript API client |
| Framework | Declarative `Resource` / `Field` API, HTML/API route generation, common validation, policies, lifecycle hooks, generated navigation and OpenAPI |
| Accounts | Registration, login, POST logout, profile/password changes, expiring reset links, hashed passwords, session revocation |
| Access | Owner-only resources and administrator-only shared resources; the same policy applies to HTML, JSON, reads, writes, and exports |
| Database | SQLAlchemy models, SQLite locally, PostgreSQL support, Alembic migrations, foreign keys, transactions, optimistic version locking |
| Content | Administrator-managed website pages, private drafts, publish/unpublish, real public URLs loaded from the database |
| Files | Private verified images, quotas, authenticated downloads, upload/delete via forms and API; small images persist in the database |
| Administration | Account activation and roles, contact messages, audit events, owner-console admin creation and password reset |
| Operations | Environment validation, security headers, CSRF, rate limits, migration readiness, request IDs, SQLite backups, WSGI/Gunicorn, Docker and CI |

The Notes module is a small example of the public resource API. The page publisher
uses the same engine with an administrator policy. Both are normal modules that
you can replace or extend without rewriting the framework.

## Create your application feature

Activate `.venv` first, or substitute `.venv\Scripts\python.exe` on Windows and
`.venv/bin/python` on macOS/Linux for `python`.

```sh
python manage.py make-resource products --field name:text --field price:decimal --field stock:integer --field available:boolean
python manage.py db migrate -m "Add products"
# Open and review the new migration, then:
python manage.py db upgrade
```

Restart. **`/app/products`** is its working frontend. **`/api/v1/products`** is its
working API. Its navigation link and OpenAPI schema are registered automatically.
The generator also writes an integration test, model, business-rule hook, and
frontend template extension. It refuses unsafe names and existing files.

Edit the generated model in `database/models/`, field contract in
`backend/modules/products/resource.py`, rules in `service.py`, and frontend in
`frontend/templates/products/`. See [Build a feature](docs/BUILD_A_FEATURE.md).

## Easy directory navigation

| Folder | What belongs here |
| --- | --- |
| `frontend/` | HTML/Jinja pages, shared components, CSS, JavaScript, images |
| `backend/framework/` | Reusable engine; application factory, definitions, policies, forms, services, generated routes, OpenAPI |
| `backend/modules/` | Your domain modules and built-in account/admin/content/file modules |
| `database/` | Models, migrations, private local data and backups |
| `scripts/` | Installer, resource generator, production startup and configuration |
| `deploy/` | Hosting entry points |
| `tests/` | Isolated behavior/security/integration tests |
| `docs/` | Opening, framework API, customization, hosting, operations, verification |

## Useful commands

```sh
python manage.py create-admin
python manage.py set-password
python manage.py resources
python manage.py routes
python manage.py check
python manage.py db check
python manage.py backup-db
```

`create-admin` prompts for your own credentials. Sign in normally to manage website
pages and accounts. Local reset mail is written privately to `instance/outbox`;
real delivery requires configured SMTP. Production email defaults to disabled,
with console password reset available at no email-service cost.

## Verify the full request cycle

Create a note through the browser, read it through `/api/v1/notes`, restart the app,
and confirm it remains. Sign in as another account and confirm it is private.
As an administrator, publish a website page and open its public URL while signed out.
These operations connect the frontend, Flask services, and migrated SQL database.

Install optional development tools and run the tests:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

Windows also has `RUN_TESTS.bat`. Tests use temporary databases, not your live data.
See [Validation](docs/VALIDATION.md) for the actual verification record and limits.

## Cost and deployment

Core use requires no paid API, Node build tool, Redis service, cloud account, or
database subscription. SQLite works locally. Optional Docker Compose starts local
PostgreSQL. [Free deployment](docs/FREE_DEPLOYMENT.md) covers PythonAnywhere with
persistent SQLite and a Render + Neon preview deployment. Free hosts have quotas,
sleep/renewal rules, and availability limits; software architecture does not remove
those limits or guarantee enterprise hosting reliability.

## Guides

- [Open and run](docs/QUICKSTART.md)
- [Architecture and directory map](docs/ARCHITECTURE.md)
- [Framework API](docs/FRAMEWORK_API.md)
- [Build a feature](docs/BUILD_A_FEATURE.md)
- [Customize the frontend](docs/FRONTEND.md)
- [JSON API](docs/API.md)
- [Free deployment](docs/FREE_DEPLOYMENT.md)
- [Operations, security settings, backups](docs/OPERATIONS.md)
- [Validation record](docs/VALIDATION.md)

This release initializes a fresh application schema. Never copy a database from
another application over it; migrate existing data deliberately if you need it.
