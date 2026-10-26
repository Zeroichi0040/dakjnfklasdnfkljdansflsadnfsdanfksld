"""Explicit authorization policies, shared by HTML pages and JSON endpoints."""

from werkzeug.exceptions import Forbidden

from database import db


class OwnerPolicy:
    """Authenticated users manage only their own records, including administrators."""

    name = "owner"

    def allows(self, actor, action="read"):
        return bool(actor.is_authenticated and actor.is_active)

    def authorize(self, actor, action="read"):
        if not self.allows(actor, action):
            raise Forbidden("Your account does not have access to this resource.")

    def query(self, model, actor):
        self.authorize(actor)
        return db.select(model).where(model.user_id == actor.id)


class AdminPolicy(OwnerPolicy):
    """Only administrators manage this shared resource, such as published pages."""

    name = "admin"

    def allows(self, actor, action="read"):
        return super().allows(actor, action) and actor.is_admin

    def query(self, model, actor):
        self.authorize(actor)
        return db.select(model)
