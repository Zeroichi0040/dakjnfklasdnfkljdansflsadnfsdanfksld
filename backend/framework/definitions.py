"""The public framework API. Declare a resource; the engine builds its full vertical slice."""

import keyword
import re
from dataclasses import dataclass, field
from typing import Callable

from backend.framework.policies import OwnerPolicy

KINDS = {"text", "textarea", "email", "url", "integer", "decimal", "boolean", "date", "choice"}
RESERVED = {
    "auth",
    "csrf",
    "me",
    "files",
    "resources",
    "openapi",
    "admin",
    "public",
    "dashboard",
    "health",
    "static",
    "account",
}
PROTECTED_FIELDS = {"id", "user_id", "version", "created_at", "updated_at", "metadata", "query"}


def valid_identifier(value):
    return (
        bool(re.fullmatch(r"[a-z][a-z0-9_]{1,29}", value))
        and not keyword.iskeyword(value)
        and not keyword.issoftkeyword(value)
    )


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    kind: str = "text"
    required: bool = False
    max_length: int = 120
    minimum: int | float | None = None
    maximum: int | float | None = None
    default: object = ""
    choices: tuple = ()
    pattern: str | None = None
    help: str = ""

    def __post_init__(self):
        if not valid_identifier(self.name) or self.name in PROTECTED_FIELDS or self.kind not in KINDS:
            raise ValueError(f"Invalid resource field: {self.name}")
        if not 1 <= self.max_length <= 100_000:
            raise ValueError("Field max_length must be between 1 and 100000.")
        if self.kind == "choice" and not self.choices:
            raise ValueError("A choice field requires choices.")
        if self.pattern:
            re.compile(self.pattern)


@dataclass(frozen=True)
class Resource:
    key: str
    label: str
    singular: str
    model: type
    fields: tuple[Field, ...]
    search: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    policy: object = field(default_factory=OwnerPolicy)
    description: str = ""
    list_template: str = "framework/resource_list.html"
    on_save: Callable | None = None
    on_delete: Callable | None = None

    def __post_init__(self):
        if not valid_identifier(self.key) or self.key in RESERVED:
            raise ValueError(f"Invalid or reserved resource name: {self.key}")
        names = [f.name for f in self.fields]
        if not names or len(names) != len(set(names)):
            raise ValueError("A resource needs unique declared fields.")
        model_fields = set(names) | (PROTECTED_FIELDS - {"metadata", "query"})
        if any(not hasattr(self.model, name) for name in model_fields):
            raise ValueError(f"Resource {self.key} model must implement OwnedRecord and its declared fields.")
        if not set(self.search).issubset(names) or not set(self.columns).issubset(names):
            raise ValueError("Search and columns must refer to declared fields.")
        for name in self.search:
            if next(f for f in self.fields if f.name == name).kind not in {
                "text",
                "textarea",
                "email",
                "url",
                "choice",
            }:
                raise ValueError("Search fields must contain text.")

    @property
    def table_fields(self):
        selected = self.columns or tuple(f.name for f in self.fields[:3])
        return tuple(f for name in selected for f in self.fields if f.name == name)
