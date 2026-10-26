"""An administrator-only CMS module. Published content is served by public routes."""

from backend.framework import AdminPolicy, Field, Resource
from database.models.page import Page

resource = Resource(
    key="pages",
    label="Website pages",
    singular="Page",
    model=Page,
    fields=(
        Field("title", "Title", required=True),
        Field(
            "slug",
            "URL name",
            required=True,
            max_length=80,
            pattern=r"[a-z0-9]+(?:-[a-z0-9]+)*",
            help="Lowercase words separated by hyphens. Published at /pages/your-url-name.",
        ),
        Field("body", "Content", kind="textarea", required=True, max_length=20000),
        Field("published", "Publish this page", kind="boolean", default=False),
    ),
    search=("title", "body"),
    columns=("title", "slug", "published"),
    policy=AdminPolicy(),
    description="Write, preview, and publish pages on the public website.",
)
