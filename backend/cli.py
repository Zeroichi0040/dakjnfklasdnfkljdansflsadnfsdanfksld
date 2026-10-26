"""Owner-only terminal commands. No command creates a public default password."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask_migrate import upgrade
from sqlalchemy.exc import SQLAlchemyError

from backend.config import ROOT
from backend.framework.readiness import assert_ready
from database import db
from database.models import AuditEvent, User
from database.repositories import user_by_email


def register_commands(app):
    @app.cli.command("init-db")
    def initialize():
        """Apply checked-in migrations. Safe to repeat; never drops data."""
        upgrade(directory=str(ROOT / "database/migrations"))
        click.echo("Database migrations applied.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True, default="Administrator")
    @click.password_option()
    def create_admin(email, name, password):
        """Create an administrator, or explicitly promote an existing account."""
        from email_validator import EmailNotValidError, validate_email  # noqa: PLC0415

        try:
            email = validate_email(email, check_deliverability=False).normalized.casefold()
        except EmailNotValidError:
            raise click.ClickException("Enter a valid email address.") from None
        if not 12 <= len(password) <= 128 or not 1 <= len(name.strip()) <= 80:
            raise click.ClickException("Use a name of 1-80 characters and a password of 12-128 characters.")
        user = user_by_email(email)
        if user:
            click.confirm("This account exists. Promote it and replace its password?", abort=True)
            user.session_version += 1
            user.role, user.active = "admin", True
        else:
            user = User(email=email, display_name=name.strip(), role="admin", active=True)
            db.session.add(user)
        user.set_password(password)
        db.session.flush()
        db.session.add(
            AuditEvent(user_id=user.id, action="owner.admin_created", subject="Administrator configured from terminal")
        )
        db.session.commit()
        click.echo("Administrator configured. Sign in through /auth/login.")

    @app.cli.command("set-password")
    @click.option("--email", prompt=True)
    @click.password_option()
    def set_password(email, password):
        """Reset an account password from the trusted owner console."""
        from backend.modules.auth.service import change_password  # noqa: PLC0415

        user = user_by_email(email)
        if not user:
            raise click.ClickException("No account matches that email.")
        if not 12 <= len(password) <= 128:
            raise click.ClickException("Use between 12 and 128 characters.")
        change_password(user, password)
        click.echo("Password changed. Previous sessions have been revoked.")

    @app.cli.command("check")
    def check_configuration():
        """Check startup and database readiness without exposing credentials."""
        try:
            assert_ready()
        except (SQLAlchemyError, RuntimeError):
            raise click.ClickException("Database is not ready. Run python manage.py db upgrade.") from None
        click.echo(f"Environment: {app.config['APP_ENV']}")
        click.echo(f"Database driver: {db.engine.dialect.name}")
        click.echo("Database readiness: OK")
        click.echo("CSRF protection: enabled")
        click.echo(f"Email delivery: {app.config['MAIL_TRANSPORT']}")
        if app.config["RATELIMIT_STORAGE_URI"] == "memory://":
            click.echo("Rate limits: per process. Use one worker, or configure shared storage before scaling.")

    @app.cli.command("backup-db")
    @click.option("--output", type=click.Path(path_type=Path), default=None)
    def backup_database(output):
        """Create a consistent SQLite backup without overwriting an existing file."""
        if db.engine.dialect.name != "sqlite" or not db.engine.url.database or db.engine.url.database == ":memory:":
            raise click.ClickException("For PostgreSQL backups, follow docs/OPERATIONS.md.")
        source = Path(db.engine.url.database)
        if not source.is_file():
            raise click.ClickException("The database does not exist yet.")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination = output or ROOT / "database/backups" / f"application-{stamp}.sqlite3"
        destination = destination.resolve()
        if destination == source.resolve():
            raise click.ClickException("Choose a different path from the live database.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("xb"):
                pass
        except FileExistsError:
            raise click.ClickException("That backup file already exists. Choose a new path.") from None
        with sqlite3.connect(str(source)) as src, sqlite3.connect(str(destination)) as target:
            src.backup(target)
        destination.chmod(0o600)
        click.echo(f"Backup created: {destination}")

    @app.cli.command("make-resource")
    @click.argument("name")
    @click.option(
        "--field",
        "fields",
        multiple=True,
        help="Repeat name:type. Types: text, textarea, email, url, integer, decimal, boolean, date.",
    )
    def make_resource(name, fields):
        """Generate a model, module, frontend extension, and integration test."""
        from scripts.scaffold import scaffold

        try:
            written = scaffold(ROOT, name, fields)
        except ValueError as error:
            raise click.ClickException(str(error)) from None
        for path in written:
            click.echo(path)
        click.echo(f'Next: python manage.py db migrate -m "Add {name}"')
        click.echo("Review the new migration, then run: python manage.py db upgrade")
        click.echo(f"Restart. HTML: /app/{name} | JSON: /api/v1/{name}")
        click.echo("Navigation and OpenAPI are registered automatically.")

    @app.cli.command("resources")
    def list_resources():
        """Show the real registered resources, routes, and permission policies."""
        from backend.framework.extension import framework

        for resource in framework().resources.values():
            click.echo(
                f"{resource.key}: HTML /app/{resource.key} | API /api/v1/{resource.key} | policy={resource.policy.name}"
            )
