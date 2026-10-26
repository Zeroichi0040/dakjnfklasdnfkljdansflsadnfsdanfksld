# Framework API

Import the public API from `backend.framework`:

```python
from backend.framework import Field, Resource, OwnerPolicy, AdminPolicy
```

## Resource

`Resource(key, label, singular, model, fields, ...)` describes one feature. Its
SQLAlchemy model inherits `OwnedRecord` and `db.Model`. The mixin supplies `id`,
`user_id`, timestamps and an optimistic `version` column.

| Option | Meaning |
| --- | --- |
| `key` | Unique lowercase resource name; `/app/<key>` and `/api/v1/<key>` |
| `label`, `singular` | Navigation/table heading and create/edit labels |
| `model` | Your SQLAlchemy model class |
| `fields` | Tuple of editable `Field` definitions; all other inputs are rejected |
| `search` | Text fields eligible for literal search |
| `columns` | Fields displayed in the list table |
| `policy` | `OwnerPolicy()` by default, or explicit `AdminPolicy()` / custom policy |
| `description` | Introductory page copy |
| `list_template` | Optional child template extending the shared list view |
| `on_save(record, actor, creating)` | Business-rule hook before save/commit |
| `on_delete(record, actor)` | Business-rule hook before deletion/commit |

Every resource has list, create, detail, edit, delete, and CSV frontend endpoints.
Its JSON API has GET/POST collection and GET/PATCH/DELETE record endpoints. Navigation,
overview counts and the API specification follow the registry automatically.

## Field

`Field(name, label, kind="text", required=False, ...)` supports:

| Kind | Input / storage guidance |
| --- | --- |
| `text`, `textarea` | Bounded strings; `max_length`, optional `pattern` regex |
| `email`, `url` | Email syntax or http(s) URL validation; bounded strings |
| `integer` | Whole numbers within signed 32-bit range; optional bounds |
| `decimal` | Finite amounts with at most two decimal places; JSON decimal strings; SQL `Numeric(12,2)` |
| `boolean` | Actual JSON true/false or a generated checkbox |
| `date` | ISO date or null; SQL Date |
| `choice` | Explicit `(value, label)` pairs, rendered as a select |

Other options: `default`, `minimum`, `maximum`, `choices`, `pattern`, and `help`.
Keep model nullability, size, and defaults consistent with the field contract.
Decimal values are serialized as strings to preserve precision. Passwords and
credentials belong in the authentication/integration layer, not generic resources.

```python
Field(
    "status", "Status", kind="choice", required=True, default="open", choices=(("open", "Open"), ("closed", "Closed"))
)
Field("price", "Price", kind="decimal", minimum=0, default="0.00")
```

## Services and hooks

`backend.framework.services` exposes `query`, `get_record`, `create`, `update`,
`delete`, and `serialize`. Pass a registered resource and authenticated actor.
The HTML/API routes call these same functions. `update` and `delete` require the
current version. Writes commit data and an audit event together or roll back.

```python
from backend.common.errors import ValidationError


def before_save(record, actor, creating):
    if record.price is not None and record.price < 0:
        raise ValidationError({"price": ["Price cannot be negative."]})
```

Hooks run **before commit**; do not send external messages or charge a payment in
them. Add an appropriate durable job/outbox integration for external side effects.
The included private mail adapter is optional; no paid job service is required.

## Policies

Owner policy includes `user_id == actor.id` in every query, even for an admin.
Admin policy permits active administrators and uses a shared query scope for CMS
content. For another access model, implement `allows(actor, action)`,
`authorize(actor, action)`, and `query(model, actor)` in a policy class. Treat the
query scope as part of authorization; hiding a link is not a permission check.
Test reads, edits, deletions, API requests, and exports for the new policy.

## Custom workflows

Keep ordinary Flask blueprints for bookings, checkout or other multi-step domain
work. Register their module in `BLUEPRINT_MODULES`. Reuse the account session,
forms, `db.session`, policies, adapters and shared errors. The resource engine is
the reusable CRUD foundation; your domain supplies its own transaction rules.
