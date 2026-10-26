# Build a feature: products

Use the project's Python from the application folder. The command below creates a
working module with text, decimal, integer and checkbox fields:

```sh
python manage.py make-resource products --field name:text --field price:decimal --field stock:integer --field available:boolean
python manage.py db migrate -m "Add products"
```

Open the new file in `database/migrations/versions/`. Confirm it creates the
intended products table and indexes; then apply it:

```sh
python manage.py db upgrade
python manage.py db check
```

Restart the server. Sign in and open `/app/products`. Add a product, edit it, view
its detail, search, export it, and delete it. The equivalent JSON endpoints are
`/api/v1/products` and `/api/v1/products/<id>`.

## Generated files

| File | Your responsibility |
| --- | --- |
| `database/models/products.py` | Stored fields, indexes and database constraints |
| `backend/modules/products/resource.py` | Labels, editable field contract, table/search fields, policy and template |
| `backend/modules/products/service.py` | Your business rules in `before_save` |
| `frontend/templates/products/index.html` | Feature-specific presentation over the shared frontend |
| `tests/test_resource_products.py` | Generated integration check; expand for your business behavior |
| `backend/module_registry.py` | Automatic resource registration |

No route copy/paste is needed for ordinary CRUD. The framework supplies forms,
list/detail/edit/delete screens, API routes, ownership checks, audit events,
pagination, version checks, navigation, and generated OpenAPI.

## Make it fit your domain

In `resource.py`, set `singular="Product"` and your desired labels. Use
`Field("price", "Price", kind="decimal", minimum=0, default="0.00")` for nonnegative
prices. Add a stock rule if your app prohibits negative stock. Monetary values use
decimal strings in JSON, not floating point. Add currency explicitly if needed.

The generated resource is private to each account by default. For a shared,
administrator-managed catalog, choose `policy=AdminPolicy()`. A public catalog
requires a deliberately public read route that selects only publishable products;
retain protected write routes. Follow the pages module for a public-read example.

For a booking system or store, implement capacity, pricing, ordering, reservation,
and payment rules as real domain services. The engine's generic CRUD cannot decide
those rules for you. Optional external providers can introduce charges.

## Add or remove fields later

Change the SQLAlchemy model and the field definition together. Generate, review
and apply another migration. Existing rows need explicit backfills before a new
non-null constraint; Python defaults alone do not update stored rows. Commit the
model, resource, tests, frontend and migration together. Deploy committed revisions
with `db upgrade`; do not autogenerate migrations on a live server.

Names must be 2–30 lowercase letters, digits or underscores, beginning with a letter.
Reserved Python/framework names and existing files are refused. `--field` supports
text, textarea, email, url, integer, decimal, boolean and date. Choice fields can be
declared directly in the resource definition with explicit choices.

## Start with your own domain

To remove the example Notes module, remove its entry from `RESOURCE_MODULES`.
To remove its stored table, create a reviewed migration after removing its model
from loaded metadata. Keep the engine in `backend/framework` and add your own
modules. The page publisher is optional too; if removing it, also update the
public page routes that use its model. Keep schema changes deliberate.
