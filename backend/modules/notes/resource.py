"""A minimal owner-scoped application module using the framework's public API."""

from backend.framework import Field, Resource
from database.models.note import Note

resource = Resource(
    key="notes",
    label="Notes",
    singular="Note",
    model=Note,
    fields=(Field("title", "Title", required=True), Field("body", "Content", kind="textarea", max_length=10000)),
    search=("title", "body"),
    columns=("title", "body"),
    description="Private notes belonging to your account.",
)
