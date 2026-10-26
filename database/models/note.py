"""Example private resource. Replace or remove its registry entry for your application."""

from database import db
from database.models.base import OwnedRecord


class Note(OwnedRecord, db.Model):
    __tablename__ = "notes"
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    __table_args__ = (db.Index("ix_notes_owner_updated", "user_id", "updated_at"),)
