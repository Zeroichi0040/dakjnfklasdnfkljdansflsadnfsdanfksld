"""Generate a complete resource module without overwriting application code."""

import re
from pathlib import Path

from backend.framework.definitions import PROTECTED_FIELDS, RESERVED, valid_identifier

TYPE_COLUMNS = {
    "text": "db.String(120)",
    "textarea": "db.Text",
    "email": "db.String(254)",
    "url": "db.String(2048)",
    "integer": "db.Integer",
    "decimal": "db.Numeric(12, 2)",
    "boolean": "db.Boolean",
    "date": "db.Date",
}


def scaffold(root, name, fields=()):
    root = Path(root).resolve()
    if not valid_identifier(name) or name in RESERVED:
        raise ValueError(
            "Use 2-30 lowercase letters, digits, or underscores; begin with a letter and avoid reserved names."
        )
    definitions = []
    for entry in fields or ("title:text", "body:textarea"):
        parts = entry.split(":")
        if len(parts) != 2 or parts[1] not in TYPE_COLUMNS:
            raise ValueError(
                "Use --field name:type with text, textarea, email, url, integer, decimal, boolean, or date."
            )
        key, kind = parts
        if not valid_identifier(key) or key in PROTECTED_FIELDS or any(x[0] == key for x in definitions):
            raise ValueError("Field names must be unique, valid, and different from protected model fields.")
        definitions.append((key, kind))
    package = root / "backend/modules" / name
    model_path = root / "database/models" / f"{name}.py"
    template_path = root / "frontend/templates" / name / "index.html"
    test_path = root / "tests" / f"test_resource_{name}.py"
    if any(path.exists() for path in [package, model_path, template_path, test_path]):
        raise ValueError("This resource already exists. No files were overwritten.")
    class_name = "".join(word.capitalize() for word in name.split("_")) + "Record"
    label = name.replace("_", " ").title()
    columns, resource_fields, values = [], [], {}
    for i, (key, kind) in enumerate(definitions):
        required = i == 0 and kind in {"text", "textarea", "email", "url"}
        max_length = {"textarea": 10000, "email": 254, "url": 2048}.get(kind, 120)
        default = (
            False
            if kind == "boolean"
            else 0
            if kind == "integer"
            else "0.00"
            if kind == "decimal"
            else None
            if kind == "date"
            else ""
        )
        nullable = kind in {"integer", "decimal", "date"}
        model_default = (
            "False"
            if kind == "boolean"
            else "0"
            if kind in {"integer", "decimal"}
            else "None"
            if kind == "date"
            else repr("")
        )
        columns.append(f"    {key} = db.Column({TYPE_COLUMNS[kind]}, nullable={nullable!r}, default={model_default})")
        resource_fields.append(
            f"        Field({key!r}, {key.replace('_', ' ').title()!r}, kind={kind!r}, required={required!r}, max_length={max_length}, default={default!r}),"
        )
        values[key] = {
            "text": "Example record",
            "textarea": "Saved through the generated API.",
            "email": "test@example.com",
            "url": "https://example.com",
            "integer": 2,
            "decimal": "12.50",
            "boolean": True,
            "date": "2026-12-01",
        }[kind]
    search = tuple(key for key, kind in definitions if kind in {"text", "textarea", "email", "url"})
    table_fields = tuple(key for key, kind in definitions if kind != "textarea")[:3] or (definitions[0][0],)
    contents = {
        package / "__init__.py": f'"""{label} application module."""\n',
        model_path: f'''"""DATABASE: {label}. Change fields here and create a reviewed migration."""
from database import db
from database.models.base import OwnedRecord


class {class_name}(OwnedRecord, db.Model):
    __tablename__ = {name!r}
'''
        + "\n".join(columns)
        + "\n",
        package / "service.py": '''"""Your domain rules run inside the framework's database transaction."""


def before_save(record, actor, creating):
    """Add business rules here. Raise ValidationError to reject and roll back a save.

    Keep external side effects out of this hook; it runs before commit.
    The shared framework already validates fields and enforces ownership.
    """
    return None
''',
        package / "resource.py": f'''"""BACKEND: one definition powers HTML, API, forms, navigation, and OpenAPI."""
from backend.framework import Field, Resource
from backend.modules.{name}.service import before_save
from database.models.{name} import {class_name}

resource = Resource(
    key={name!r}, label={label!r}, singular={label!r}, model={class_name},
    fields=(
'''
        + "\n".join(resource_fields)
        + f"""
    ),
    search={search!r}, columns={table_fields!r},
    list_template={name + "/index.html"!r}, on_save=before_save,
    description={"Manage your " + label.lower() + " records."!r},
)
""",
        template_path: """{% extends "framework/resource_list.html" %}
{% block resource_intro %}
  <p>{{ resource.description }}</p>
{% endblock %}
""",
        test_path: f'''"""Generated integration test. Uses the application's isolated test fixtures."""
from tests.conftest import api_request, login


def test_{name}_resource(client, users):
    login(client)
    result = api_request(client, "POST", "/api/v1/{name}", {values!r})
    assert result.status_code == 201, result.get_data(as_text=True)
    identifier = result.json["data"]["id"]
    assert client.get(f"/api/v1/{name}/{{identifier}}").status_code == 200
    assert client.get("/app/{name}").status_code == 200
    assert api_request(client, "DELETE", f"/api/v1/{name}/{{identifier}}", {{"version": 1}}).status_code == 204
''',
    }
    registry = root / "backend/module_registry.py"
    previous = registry.read_text(encoding="utf-8")
    match = re.search(r"RESOURCE_MODULES\s*=\s*\[(.*?)\]", previous, re.S)
    if not match or f"backend.modules.{name}.resource" in previous:
        raise ValueError("The resource registry is not in the expected format, or the resource is already registered.")
    insertion = match.end() - 1
    addition = f'    "backend.modules.{name}.resource:resource",\n'
    written, directories = [], []
    try:
        for path, content in contents.items():
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
                directories.append(path.parent)
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
            written.append(path)
        registry.write_text(previous[:insertion] + addition + previous[insertion:], encoding="utf-8")
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        for directory in reversed(directories):
            try:
                directory.rmdir()
            except OSError:
                pass
        registry.write_text(previous, encoding="utf-8")
        raise
    return [p.relative_to(root).as_posix() for p in written] + ["backend/module_registry.py"]
