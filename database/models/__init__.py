"""Core models; resource model imports are loaded by the framework registry."""

from database.models.support import Attachment, AuditEvent, Inquiry, SiteState
from database.models.user import User

__all__ = ["User", "Attachment", "AuditEvent", "Inquiry", "SiteState"]

# Imported for migration metadata; not part of the generic resource engine.
from database.models.bakery import Category, Order, OrderItem, Payment, Product  # noqa: F401, E402
