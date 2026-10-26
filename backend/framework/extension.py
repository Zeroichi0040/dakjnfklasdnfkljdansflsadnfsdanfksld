"""An application-local Flask extension, not a global application singleton."""

from importlib import import_module

from flask import current_app

from backend.framework.definitions import Resource
from backend.framework.routes import build_api, build_html


class Framework:
    def __init__(self, app=None):
        self.resources = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if "fullstack" in app.extensions:
            raise ValueError("Framework is already initialized for this application.")
        app.extensions["fullstack"] = self
        for target in app.config["RESOURCE_MODULES"]:
            module, name = target.split(":", 1)
            self.register(app, getattr(import_module(module), name))

    def register(self, app, resource):
        if not isinstance(resource, Resource) or resource.key in self.resources:
            raise ValueError("Register unique Resource definitions.")
        self.resources[resource.key] = resource
        app.register_blueprint(build_html(resource))
        app.register_blueprint(build_api(resource))


def framework():
    return current_app.extensions["fullstack"]
