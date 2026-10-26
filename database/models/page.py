"""Administrator-managed content, published to real public URLs."""

from database import db
from database.models.base import OwnedRecord


class Page(OwnedRecord, db.Model):
    __tablename__ = "pages"
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(80), nullable=False, unique=True)
    body = db.Column(db.Text, nullable=False, default="")
    published = db.Column(db.Boolean, nullable=False, default=False, index=True)
