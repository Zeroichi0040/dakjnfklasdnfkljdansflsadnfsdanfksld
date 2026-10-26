# Database

Models are in `models`; committed revisions are in `migrations`. Apply revisions
with `python manage.py db upgrade`. SQLite data lives privately in
`data/application.sqlite3`; optional PostgreSQL uses `DATABASE_URL`.
`OwnedRecord` supplies ownership, timestamps and version locking to resources.
See `../docs/OPERATIONS.md` before schema changes, backups or restores.
