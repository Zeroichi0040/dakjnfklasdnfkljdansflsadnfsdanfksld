"""Framework terminal entry point. Run --help to list available commands."""

from flask.cli import FlaskGroup

from backend import create_app

cli = FlaskGroup(create_app=create_app)

if __name__ == "__main__":
    cli()
