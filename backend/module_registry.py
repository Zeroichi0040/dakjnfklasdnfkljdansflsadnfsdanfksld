"""Your application composition. Generated resources are registered here automatically."""

BLUEPRINT_MODULES = [
    "backend.modules.public.routes",
    "backend.modules.shop.routes",
    "backend.modules.auth.routes",
    "backend.modules.account.routes",
    "backend.modules.dashboard.routes",
    "backend.modules.admin.routes",
    "backend.modules.files.routes",
    "backend.modules.api.routes",
    "backend.modules.health.routes",
]

RESOURCE_MODULES = [
    "backend.modules.notes.resource:resource",
    "backend.modules.pages.resource:resource",
]
