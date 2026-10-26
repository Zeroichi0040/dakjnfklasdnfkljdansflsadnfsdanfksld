# JSON API

Open `/api/docs` in the running app. `/api/openapi.json` is generated from the live
resource registry, so generated features appear without editing a separate JSON file.
`GET /api/v1/resources` lists resources available to the authenticated account.

## Browser client

On your application's origin, while signed in:

```js
const { api } = await import('/static/js/api-client.js');
const created = await api('/api/v1/notes', {
  method: 'POST', body: { title: 'First note', body: 'Saved in SQL.' }
});
const record = created.data;
await api(`/api/v1/notes/${record.id}`, {
  method: 'PATCH', body: { version: record.version, body: 'Updated in SQL.' }
});
```

The helper retains the session cookie, obtains CSRF, handles JSON errors, and accepts
only same-origin `/api/v1/` URLs. Its `body` also accepts FormData for image upload.

## Authentication

1. `GET /api/v1/csrf`; keep the session cookie and returned token.
2. `POST /api/v1/auth/login` with JSON email/password and `X-CSRFToken`.
3. Use the **new** CSRF token returned by login; sign-in rotates the session.
4. `GET /api/v1/me` reads safe account fields. `POST /api/v1/auth/logout` signs out.

Every POST/PATCH/DELETE requires CSRF plus the same cookie, including file uploads.
The API is designed for a same-origin browser client. No wildcard CORS or bearer
tokens are enabled. Use the registration page to create accounts; sign-up cannot
choose an administrator role.

## Generated resource contract

| Request | Result |
| --- | --- |
| `GET /api/v1/<resource>` | Own/authorized records in `data`, with `pagination` |
| `POST /api/v1/<resource>` | Validated creation, 201 and Location |
| `GET /api/v1/<resource>/<id>` | Record in `data`, version ETag |
| `PATCH /api/v1/<resource>/<id>` | Selected editable fields plus current `version` |
| `DELETE /api/v1/<resource>/<id>` | JSON `{"version": 1}`; permanent deletion, 204 |

Only declared fields are editable. Owner IDs, timestamps and versions are assigned
by the server. Unknown fields are rejected. List parameters: `q` (up to 120),
`sort` (declared sortable field, optionally prefixed with `-`), `page` (positive),
and `per_page` (1–50). Text search treats SQL `%` and `_` literally.

Send decimal fields as strings, such as `"19.95"`; dates as `YYYY-MM-DD` or null;
booleans as true/false. Read the current version before editing. A stale version
returns 409, allowing the user to reload and reconcile changes rather than silently
overwrite another request. Invalid data returns 422 with field errors.

Errors contain `error.status`, `error.message`, `error.fields`, and a request ID.
Other statuses include 400 (CSRF/malformed request), 401 (login), 403 (policy),
404 (missing or unavailable record), 415 (content type), and 429 (rate limit).
No password hash or reset token is returned by profile/resource endpoints.

## Files

`GET /api/v1/files` lists private image metadata; `POST /api/v1/files` accepts a
multipart `file`; `DELETE /api/v1/files/<uuid>` removes an owned image. Its download
URL is `/files/<uuid>/download` and requires the same authenticated owner. PNG/JPEG/
WebP are verified, bounded by size/pixels, and limited by an atomic per-user quota.

HTML CSV exports honor the current search and sort, include at most 5,000 authorized
records, and stream rows to bound memory. Use paginated JSON for larger exports.
