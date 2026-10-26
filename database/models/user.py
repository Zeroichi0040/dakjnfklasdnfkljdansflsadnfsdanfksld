"""DATABASE: real accounts, hashed passwords, and revocable sessions."""

from datetime import datetime, timezone

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from database import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, unique=True)
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="member")
    active = db.Column(db.Boolean, nullable=False, default=True)
    storage_bytes = db.Column(db.Integer, nullable=False, default=0)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": session_version, "version_id_generator": False}
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.CheckConstraint("role IN ('member', 'admin')", name="valid_role"),)

    @property
    def is_active(self):
        return self.active

    @property
    def is_admin(self):
        return self.active and self.role == "admin"

    def get_id(self):
        # Changing a password or account status invalidates all previous sessions.
        return f"{self.id}:{self.session_version}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method=current_app.config["PASSWORD_HASH_METHOD"])

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
