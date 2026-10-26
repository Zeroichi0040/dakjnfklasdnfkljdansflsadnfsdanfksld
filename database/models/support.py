"""DATABASE: audit trail, contact messages, private files, and admin serialization."""

import uuid

from database import db
from database.models.user import utcnow


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(60), nullable=False)
    subject = db.Column(db.String(160), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class Inquiry(db.Model):
    __tablename__ = "inquiries"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    message = db.Column(db.Text, nullable=False)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class Attachment(db.Model):
    __tablename__ = "attachments"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(120), nullable=False)
    content_type = db.Column(db.String(40), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    # Small private images remain durable on hosts with an ephemeral filesystem.
    # Move large media to an object-storage adapter when your application grows.
    data = db.Column(db.LargeBinary, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class SiteState(db.Model):
    __tablename__ = "site_state"
    id = db.Column(db.Integer, primary_key=True)
    revision = db.Column(db.Integer, nullable=False, default=0)
