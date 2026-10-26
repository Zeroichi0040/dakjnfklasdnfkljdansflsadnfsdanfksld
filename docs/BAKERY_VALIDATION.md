# Bakery validation record

Validated on 2026-10-26 using Linux, Python 3.12.14, the repository's pinned
requirements and local Chromium. This record describes executed checks, not a
production deployment or certification. See the original VALIDATION.md for the
framework's earlier baseline.

| Check | Executed outcome |
| --- | --- |
| Initial unchanged framework baseline | 101 passed, 1 optional live PostgreSQL test skipped |
| Final complete pytest suite | **150 passed, 1 skipped** in 16.58 seconds; 49 new bakery cases |
| Ruff | `python -m ruff check .` passed |
| Dependency consistency | `python -m pip check` passed |
| Whitespace | `git diff --check` passed |
| Alembic schema/model comparison | `python manage.py db check` passed, no new operations |
| Fresh and repeated schema | Bakery roundtrip test downgraded/upgraded only its disposable empty test database, compared metadata and seeded successfully |
| Installer | Updated `scripts/bootstrap.py --dev` executed successfully, applied readiness checks and seeded; repeat preserved private settings and stock |
| Seed | First call added 12 products/five categories; repeat added zero; stock changes preserved in automated test |
| Live local server | Actual Waitress launcher served expected HTTP 200 responses for liveness, readiness, landing, catalogue, product detail and basket |
| Browser layouts | 60 route/viewport combinations across 320, 390, 768 and 1440 pixels; no document overflow |
| Browser customer workflow | Add anonymously, register, retain basket, checkout successfully, see persisted receipt and history |
| Browser administration | Sign in as admin, prepare/ready/complete order, view paid sales, edit stock |
| Browser failed payment | Declined simulation saved failed payment/cancelled order and reported stock restoration |
| Browser no stock | Sold-out product's purchase button disabled |
| Progressive enhancement | Real cart form submission succeeded with JavaScript disabled |
| Browser errors | No page errors or console errors in final completed browser run |
| Screenshots | Inspected full desktop/mobile landing screenshots; receipt and finance screenshots also captured in temporary artifacts |
| Concurrent stock | Two independent connections competing for the final unit produced one order and one rejection, stock zero |
| Concurrent duplicate submit | Same user/token created one order and one stock deduction |
| Transaction rollback | Forced failure after reservation rolled back stock, order and order items |
| Restoration | Cancellation/refund restored once; restoration after available-stock replenishment passed |
| Permissions | Other customer cannot view/cancel order; member cannot access/create admin inventory; admin can manage orders |
| Money | Server prices override submitted totals; receipt snapshots survive catalogue edits; failed/refunded/unpaid orders excluded from completed sales |
| Session cookie regression | Static responses do not refresh an older cookie over a newly created checkout token |

Browser checks ran against a separate disposable SQLite database with temporary
accounts. Those accounts/passwords were not installed in the development database
or committed. Browser artifacts are temporary, not application dependencies.
The development database was migrated and populated with sample products only;
no default customer or administrator was created there.

## Scope limits

The optional live PostgreSQL integration test was skipped because TEST_POSTGRES_URL
was not supplied. Offline PostgreSQL migration compilation ran in the ordinary
suite. Bakery concurrency was verified on SQLite; the existing opt-in PostgreSQL
test targets framework resources and does not replace bakery integration testing.
Windows/macOS, Docker, real SMTP delivery, a production gateway, real refunds,
load testing and a full assistive-technology/WCAG audit were not performed. Windows
batch launchers remain intact and documented; source portability is not a claim of
an executed Windows test. Payment/collection/refund are intentional simulations.

## Repeat

From the repository with its virtual environment active:

```sh
python scripts/bootstrap.py --dev
python -m pytest -q
python -m ruff check .
python manage.py db check
python manage.py check
python run.py --no-browser
```

Use the browser walkthrough in [BAKERY_DEMO.md](BAKERY_DEMO.md). Tests use temporary
databases; never downgrade a live database to reproduce the migration test.
