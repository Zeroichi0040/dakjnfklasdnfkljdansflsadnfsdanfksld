"""Application entry point. Configure modules in module_registry.py."""

from backend.framework.application import create_application


def create_app(test_config=None):
    return create_application(test_config)
