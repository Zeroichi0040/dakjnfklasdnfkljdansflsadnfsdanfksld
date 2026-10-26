# Operations

## Environments and secrets

Setup generates `.env` with a unique secret and keeps it on repeat runs. Only
`.env.example` belongs in Git. Public production requires a persistent secret of
at least 32 characters, HTTPS, secure cookies, the correct trusted hostname, and
an explicitly trusted proxy count. `wsgi.py` and the production start script default
to production configuration. Never enable debug for a public deployment.

`scripts/configure_production.py --url https://YOUR_HOST --proxy-hops 1` prepares
private production settings. Set PostgreSQL's URL privately if needed. The script
defaults to disabled mail; configure SMTP separately only when your host permits it.
The local installer does not automatically migrate a production database.

## Schema and readiness

`python manage.py db upgrade` applies committed revisions. `db check` compares
models with the current schema. The factory does not create tables implicitly.
The readiness check validates both the initial application state and applied
migration heads. `/health/live` checks the process without querying the database;
`/health/ready` returns 503 if the schema is not ready. Liveness polling therefore
does not continually wake a sleeping external database.

Before an update: back up, install dependencies in isolation, run tests, review the
migration, apply committed revisions, restart, and verify readiness. Do not generate
migrations at every deployment. Keep each application's database and environment separate.

## SQLite backups and restore

Blank `DATABASE_URL` selects the absolute project path
`database/data/application.sqlite3`. WAL, foreign keys and a busy timeout are enabled.

```sh
python manage.py backup-db
python manage.py backup-db --output /private/path/new-backup.sqlite3
```

The SQLite backup API includes committed WAL data and refuses existing destinations
or the live database path. A backup contains private accounts, hashes, messages,
records, and images. Keep copies off the host and practice restoration separately.

To restore: stop all app processes; preserve the current database; move the old
database and its `-wal`/`-shm` sidecars aside; copy the consistent backup to the live
path; do not mix it with old sidecars. Apply migrations, run `check`, and restart.

## PostgreSQL

Use the provider connection string, including `sslmode=require` for a remote
internet database. The app accepts `postgresql://` and selects psycopg. Changing
the connection URL does not transfer SQLite rows. For existing data, plan a real
export/import into explicitly assigned accounts. Use provider exports or matching
`pg_dump`/`pg_restore` tools for backups; keep credentials out of shell history.

## Accounts and files

`create-admin` creates or explicitly promotes an account through the trusted console.
`set-password` changes a known account's password and revokes prior sessions. Members
cannot set roles through registration/profile/resource fields. An administrator
cannot change their own role/status through the UI; concurrent role changes are
serialized by a database write and rechecked authorization.

Small images are stored with SQL data, so an external PostgreSQL database also
preserves images when an app host restarts. Defaults: 2 MiB per image, 16 megapixels,
20 MiB per user, verified non-animated PNG/JPEG/WebP. Large media needs an appropriate
storage adapter and capacity plan. Contact submissions and audit rows also consume
space; define retention for your actual application.

## Logs, limits and capacity

Request logs use route patterns, timings and request IDs rather than raw token URLs
or query/body values. Database parameter values are hidden from SQL error output.
Host access logs are configured separately. Audit events are ordinary application
records, not a tamper-proof compliance ledger.

The default limiter is per process. Included deployments use one worker with threads.
Before scaling across workers/hosts, configure a shared supported limiter store and
test concurrency. SQLite suits small single-host apps; use PostgreSQL for multiple
hosts or more write concurrency. Free-plan quotas and reliability limits still apply.

Optional checks: `python -m pip_audit -r requirements.txt`. Pinned dependencies need
regular review; an audit result is dated, not a permanent security guarantee.
