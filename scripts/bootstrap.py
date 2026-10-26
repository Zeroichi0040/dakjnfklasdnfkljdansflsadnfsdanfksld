"""Standard-library-only setup. Run with a supported Python before installing Flask."""

import argparse
import os
import secrets
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="Also install the test and lint tools.")
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info[:2] < (3, 15):
        print("Install Python 3.12 or 3.13 (supported: 3.11-3.14), then run setup again.")
        return 1
    os.chdir(ROOT)
    environment = ROOT / ".env"
    if not environment.exists():
        content = (ROOT / ".env.example").read_text(encoding="utf-8")
        content = content.replace("SECRET_KEY=", "SECRET_KEY=" + secrets.token_hex(32), 1)
        content = content.replace("POSTGRES_PASSWORD=", "POSTGRES_PASSWORD=" + secrets.token_urlsafe(24), 1)
        environment.write_text(content, encoding="utf-8")
        environment.chmod(0o600)
        print("Created private .env settings with a new random key.")
    else:
        print("Keeping your existing .env settings.")
    destination = ROOT / ".venv"
    executable = destination / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        print("Creating the project's private Python environment...")
        venv.EnvBuilder(with_pip=True).create(destination)
    requirements = "requirements-dev.txt" if args.dev else "requirements.txt"
    subprocess.run(
        [str(executable), "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir", "-r", requirements],
        check=True,
    )
    # The local installer must not silently apply changes to a production database.
    from_values = dict(
        line.strip().split("=", 1)
        for line in environment.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    if os.getenv("APP_ENV", from_values.get("APP_ENV", "development")).strip().strip("\"'") == "production":
        print("Dependencies installed. For production, explicitly run: python manage.py db upgrade")
        return 0
    subprocess.run([str(executable), "manage.py", "db", "upgrade"], check=True)
    subprocess.run([str(executable), "manage.py", "check"], check=True)
    subprocess.run([str(executable), "manage.py", "bakery", "seed"], check=True)
    print("\nSETUP COMPLETE. Run START_WEBSITE.bat or bash start.sh.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        print(
            f"\nSetup stopped because a command failed (exit {error.returncode}). Check the message above; do not delete your database."
        )
        raise SystemExit(error.returncode) from None
