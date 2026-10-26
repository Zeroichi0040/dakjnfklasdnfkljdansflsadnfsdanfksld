# Free deployment

Checked against official provider documentation on **2026-10-23**. The framework
requires no paid API or database subscription to run locally. Free hosting has
quotas, renewal/sleep rules and availability limits; choose only Free resources
and review current terms before creating anything. No account or deployment is
created by running this archive locally.

## PythonAnywhere Free + persistent SQLite

This is the simpler small-app route. The [free account features](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/)
include one web app, 512 MiB disk, limited CPU and a one-month expiry requiring
renewal. The persistent home directory can hold this app's SQLite database. New
free accounts do not include MySQL; this framework does not require it.

1. Create a free account at [PythonAnywhere](https://www.pythonanywhere.com/pricing/).
   Upload this source ZIP, open a Bash console, and run:

   ```sh
   unzip Flask_Fullstack_Framework.zip
   cd ~/Flask_Fullstack_Framework
   python3.13 -m venv .venv
   .venv/bin/python -m pip install --no-cache-dir -r requirements.txt
   ```

   Use an available supported Python version, matching the Web tab's choice. Do not
   upload your computer's `.venv`. Keep source, environment, data and backups within
   the account's disk quota.

2. Replace the hostname with your assigned one:

   ```sh
   .venv/bin/python scripts/configure_production.py --url https://YOUR_USERNAME.pythonanywhere.com --proxy-hops 1
   .venv/bin/python manage.py db upgrade
   .venv/bin/python manage.py check
   .venv/bin/python manage.py create-admin
   ```

   Use the exact regional/provider hostname your account receives. Keep
   `DATABASE_URL` blank for persistent SQLite. The script generates a private
   production secret, HTTPS cookies, trusted host and disabled email.

3. Web → Add a new web app → provider domain → **Manual configuration**. Choose the
   same Python version. Set Virtualenv to
   `/home/YOUR_USERNAME/Flask_Fullstack_Framework/.venv`.
4. Replace the Web tab's sample WSGI file with `deploy/pythonanywhere_wsgi.py`,
   updating `YOUR_USERNAME`. Reload the app. Do not run `app.run()` in WSGI.
5. Open the HTTPS site and `/health/ready`. Register a member, sign in as your admin,
   and test creating a private record and publishing a page. Flask serves its static
   assets; never map `database`, `instance`, `.env`, or the project root as static.
6. Renew before the free app's expiry, monitor disk/CPU, and download private backups
   off the host. Use `.venv/bin/python manage.py set-password` for console resets.

Free accounts have [outbound-network restrictions](https://www.pythonanywhere.com/whitelist/).
The default app makes no external API calls. SMTP may be unavailable; disabled mail
and console resets work without an email provider. The official
[Flask hosting guide](https://help.pythonanywhere.com/pages/Flask/) explains WSGI and
virtual-environment configuration if the dashboard changes.

## Render Free + Neon Free PostgreSQL

This route supports a Git-based preview with a separate database. Render explicitly
positions [free instances](https://render.com/docs/free) for previews/hobby use,
rather than production. Idle services sleep, and local files disappear on restart,
redeploy or sleep. The framework therefore refuses SQLite on Render. Render's own
free Postgres expires after 30 days; use an external database for persistent data.

1. Create a Free project at [Neon](https://neon.com/pricing). Copy its private
   connection string, preserving `sslmode=require` and other provider parameters.
   The framework accepts `postgresql://` and chooses psycopg automatically.
2. Upload source to your Git repository, including migrations and `render.yaml`.
   Exclude `.env`, `.venv`, runtime databases, private outbox mail and backups.
3. In Render choose **New → Blueprint**, connect the repo, inspect the proposed web
   service and confirm the plan is **Free**. Supply `DATABASE_URL` with the Neon URL.
   No paid disk, Redis, or Render database is needed for the included deployment.
4. The blueprint installs requirements, sets production flags, generates a persistent
   secret, and starts `scripts/start_production.py`. This applies committed
   migrations and runs one Gunicorn worker with four threads. Render's assigned
   hostname supplies the public origin automatically.
5. Verify `/health/ready`, create a record, restart, and confirm it remains. Images
   persist in the external SQL database as well. Create an admin from a trusted
   environment with the same private production settings and database URL; free-host
   shell availability varies. Never create a public HTTP admin-promotion shortcut.

Neon Free has compute, storage and transfer quotas; review its current plan. Routine
health checks use `/health/live`, which does not query PostgreSQL. Do not add uptime
pings to evade free-provider sleep rules. Keep private backup copies outside the
host and monitor database growth, image quotas, contact messages and audit history.

## Optional local Docker

Docker is optional. After local setup has generated `.env`, run:

```sh
docker compose up --build
```

Open http://localhost:8000. Compose starts local PostgreSQL and the app, with a named
database volume and the app port bound only to your computer. It needs no cloud
subscription. Do not copy local HTTP cookie overrides to a public site; configure
its actual HTTPS origin and secure cookies. Docker Desktop has its own organization
licensing terms; the Python/SQLite route does not require it.

Production capacity, shared rate-limit storage, large media, custom domains,
payments, email delivery and external services depend on your chosen application
and provider terms. They are optional integrations, not hidden subscriptions in
the framework. Free plans do not provide unlimited commercial reliability.
