# Verification record

Checked on **2026-10-24** using Linux, Python **3.12.14**, and Chromium **140**.

| Check | Actual result |
| --- | --- |
| Automated suite | **101 passed**, one optional live-PostgreSQL check skipped |
| Python lint | Ruff passed |
| Dependencies | Runtime audit reported no known vulnerabilities at check time |
| Fresh installation | New private environment, runtime dependencies, unique settings, SQL migrations and readiness passed |
| Repeat installation | Passed and preserved private settings/data |
| Local launcher | Immediate same-port restart regression passed with the real Waitress server |
| Framework generator | An isolated products module with text, decimal, integer, boolean and date fields migrated and passed HTML/API create/read/update/delete, export, policy, navigation and generated OpenAPI checks; its generated integration test also passed |
| SQLite migrations | Fresh/repeated upgrades and schema/model comparison passed |
| PostgreSQL schema | Initial migration compiled successfully to PostgreSQL SQL |
| Browser writes | Sign-in, generated form create/edit, real API table refresh, private image upload/download and administrator page publishing passed |
| Public content | An anonymous browser read the published SQL-backed page |
| Responsive browser | 52 route/viewport combinations at 320, 390, 768 and 1440 pixels; overflow and header spacing checked |
| Progressive enhancement | Navigation and rendered data worked in a small-screen browser with JavaScript disabled |
| Browser errors | No JavaScript or CSP errors in the completed verification |
| Deployment files | Compose, Render and CI YAML parsed; Python source parsed |
| Distribution | Source-only archive integrity, clean extraction, database initialization, and fresh extracted-app startup checked; private runtime data excluded |

The suite covers account rules, normalized email uniqueness, hashing, CSRF, safe
redirects, session/token rotation, password reset expiry/reuse, session revocation,
disabled users/signup, owner/admin policies, protected fields, all supported value
types, validation, stale updates, SQL-level version locking, rollback hooks, atomic
audit writes, pagination, safe sort/search, escaped output, filtered CSV/formula
handling, verified image quotas, private files, administrator access, contact
management, health/configuration, backups, per-process rate limits, and safe error
responses when loading the user fails.

## Verification limits

Live PostgreSQL was unavailable in this environment. A guarded integration test and
a disposable PostgreSQL 17 CI job are included; offline SQL compilation does not
replace running that job. Windows/macOS and Docker were unavailable locally. The
underlying Python installer/server were executed on Linux; Windows batch files use
CRLF, and CI includes Windows/Python combinations and a noninteractive launcher check.

No public hosting account was created, no deployment was published, and no SMTP
delivery was performed. Deployment instructions use the linked official provider
documentation. This record is not a penetration test, load certification, SLA, or
a guarantee that dependency/provider terms remain unchanged.

## Repeat

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m pip_audit -r requirements.txt
```

For live PostgreSQL, set `TEST_POSTGRES_URL` to a disposable PostgreSQL database
whose name ends in `_test`, then run `python -m pytest -q -m postgres`. The check
refuses other database names and does not delete test records. Never point it at
a real deployment. CI creates a fresh service database for that job.
