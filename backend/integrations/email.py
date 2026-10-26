"""Email adapter. The development outbox is private and does not send email."""

import secrets
import smtplib
from email.message import EmailMessage
from pathlib import Path

from flask import current_app


def send_message(recipient, subject, body):
    config = current_app.config
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = config["MAIL_FROM"] or "development@example.invalid"
    message["Subject"] = subject
    message.set_content(body)
    if config["MAIL_TRANSPORT"] == "outbox":
        outbox = Path(current_app.instance_path) / "outbox"
        outbox.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = outbox / f"{secrets.token_hex(16)}.eml"
        path.write_bytes(message.as_bytes())
        path.chmod(0o600)
        return
    if config["MAIL_TRANSPORT"] != "smtp":
        raise RuntimeError("Email delivery is disabled.")
    with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=10) as server:
        if config["MAIL_USE_TLS"]:
            server.starttls()
        if config["MAIL_USERNAME"]:
            server.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        server.send_message(message)
