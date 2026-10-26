"""Prepare a private production .env without printing secrets or contacting a host."""

import argparse
import secrets
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", required=True, help="Your full HTTPS site origin, e.g. https://name.pythonanywhere.com"
    )
    parser.add_argument("--proxy-hops", type=int, choices=[0, 1, 2], default=1)
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        parser.error("Use an HTTPS origin without a path, credentials, query, or fragment.")
    env = ROOT / ".env"
    content = env.read_text(encoding="utf-8") if env.exists() else (ROOT / ".env.example").read_text(encoding="utf-8")
    values = dict(
        line.split("=", 1) for line in content.splitlines() if "=" in line and not line.lstrip().startswith("#")
    )
    key = values.get("SECRET_KEY", "").strip().strip("\"'")
    if values.get("APP_ENV", "").strip().strip("\"'") != "production" or len(key) < 32:
        key = secrets.token_hex(32)
    updates = {
        "APP_ENV": "production",
        "SECRET_KEY": key,
        "PUBLIC_BASE_URL": args.url.rstrip("/"),
        "SESSION_COOKIE_SECURE": "true",
        "TRUSTED_HOSTS": parsed.hostname,
        "PROXY_FIX_HOPS": str(args.proxy_hops),
        "MAIL_TRANSPORT": "disabled",
    }
    lines = []
    for line in content.splitlines():
        name = line.split("=", 1)[0] if "=" in line and not line.lstrip().startswith("#") else None
        lines.append(f"{name}={updates.pop(name)}" if name in updates else line)
    lines.extend(f"{k}={v}" for k, v in updates.items())
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    env.chmod(0o600)
    print("Private production settings written. No credentials were printed.")
    print("Set DATABASE_URL in .env if using PostgreSQL. Never upload .env to GitHub.")
    print("Next: python manage.py db upgrade, then python manage.py check")


if __name__ == "__main__":
    main()
