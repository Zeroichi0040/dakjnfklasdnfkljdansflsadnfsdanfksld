# Customize the frontend

The frontend is server-rendered Jinja plus local CSS and JavaScript. No Node build
server or CDN is required. Ordinary forms work without JavaScript; the Refresh
button reads real JSON from the backend and safely updates table cells.

| Change | File |
| --- | --- |
| Name and tagline | Private `.env`: `APP_NAME`, `APP_TAGLINE`, then restart |
| Colors, font stack and radius | `frontend/static/css/tokens.css` |
| Layout and components | `frontend/static/css/app.css` |
| Shared document, header, footer | `frontend/templates/base.html` |
| Application navigation | `frontend/templates/components/sidebar.html`; resources are automatic |
| Resource screens | `frontend/templates/framework/resource_*.html` |
| One feature's list | Generated child template in `frontend/templates/<feature>/` |
| Dashboard | `frontend/templates/dashboard/index.html` |
| Public home | `frontend/templates/public/home.html` |
| Frontend API requests | `frontend/static/js/api-client.js` |
| Mobile navigation and refresh controller | `frontend/static/js/app.js` |
| Favicon | `frontend/static/images/favicon.svg` |

## Reuse the built-in components

`components/forms.html` provides labeled controls with validation errors. The base
layout supplies flash notifications, keyboard focus, skip navigation, account
navigation, and CSRF metadata. The table and pagination support narrow screens.
Generated modules extend these screens, so improvements apply consistently.

```jinja
{% extends "framework/resource_list.html" %}
{% block resource_intro %}
  <p>Manage your store's product catalog.</p>
{% endblock %}
```

Use escaped `{{ value }}` for database/user content. Do not mark submissions as
safe HTML. The browser refresh controller uses `textContent`, not interpolated HTML.
The default content-security policy permits local scripts/styles. Put behavior in
local JS files instead of inline event handlers. New integrations must be reviewed
before adding external origins to that policy.

## Publish your website content

Create an administrator with `python manage.py create-admin`. Sign in, open
**Website pages**, add a title, URL name and content, then check Publish. The page
appears at `/pages/<url-name>` and on the home page. Unpublish makes it unavailable
to visitors. Draft content is visible only to administrators. Content is escaped
plain text with preserved line breaks; add a reviewed renderer if you need rich text.

The privacy page describes the framework's actual storage behavior. Edit its copy
for your application's practices before publishing your own site.
