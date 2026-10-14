# Building layouts and using helpers

Combine Jinja syntax with Orionis services while keeping business logic outside presentation.

## Compose reusable layouts

Templates use Jinja2, with `{{ value }}` expressions and `{% ... %}` statements. Prepare data in a controller or service; avoid expensive queries inside each iteration. The async environment automatically awaits async callables: write `{{ route("users.edit", id=user.id) }}`. Python's `await` keyword is not part of template expressions.

Create `resources/views/layouts/base.html`:

```html
<!doctype html>
<html lang="en">
<head><title>{% block title %}Reports{% endblock %}</title></head>
<body>
  {% include "partials/navigation.html" %}
  <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

Create `partials/navigation.html` with navigation, and `reports/index.html` with:

```html
{% extends "layouts/base.html" %}
{% block title %}Recent reports{% endblock %}
{% block content %}
  <ul>
  {% for report in reports %}
    <li>{{ report.title }}</li>
  {% else %}
    <li>No reports yet.</li>
  {% endfor %}
  </ul>
{% endblock %}
```

Return `await View.make("reports.index", reports=reports)`. `extends` reuses the layout and `block` replaces a region; `include` inserts another template. A loop's `{% else %}` handles empty collections. Use Jinja macros for parameterized fragments; Orionis adds no proprietary component syntax or Blade directives.

## Application helpers

The following names are registered during `ViewServiceProvider.boot()`. Helpers resolving requests, sessions, or services need those components active; constructing an isolated `Jinja2Engine` is insufficient.

| Task | Available helpers |
|---|---|
| Routes and links | `route(name, **params)`, `url(path="/", **query)`, `secure_url(path="/", **query)` |
| Assets | `asset(path, disk=None)`, `secure_asset(path, disk=None)`; default disk `public`. |
| Authentication | `auth()` returns the facade; `auth().user()`, `.check()`, `.guest()`. |
| Request / session | `request()`, `session()`; may return `None` outside scope. |
| Forms | `old(key, default=None)`, `errors.any/has/get/first/all`, `flash(key, default=None)` |
| CSRF | `csrf_token()`, `csrf_field()`, `{% csrf %}`; hidden field name `_csrf`. |
| Translation | `trans(key, locale=None, **replace)`, `__(...)`, `choice(key, count, locale=None, **replace)`, `locale()`, `locales()` |
| Global state | `app()`, `config(key, default=None)`, `cache(key, default=None)` |
| Data and diagnostics | `collect(value=None)`, `stringable(value="")`, `dump(*values)` |
| Dates/versions | `now()`, `today()`, `framework_version()`, `python_version()` |
| Encryption | `encrypt(plaintext)`, `decrypt(payload)` |

`route` path values are encoded; remaining parameters become a query string. Missing routes or required arguments raise `ViewRouteException`. URLs use the current request's origin when available and may be relative outside scope. `secure_url` upgrades to HTTPS when a host exists; it does not discover a host for a relative path. `asset` asks the disk for `file.url()`: it neither checks existence nor publishes the file.

`cache(key, default)` treats `None` as a miss. `errors` is a bag with methods, not a dict. `old` returns an empty string for `None`. `auth()` does not cache identity and preserves request scope; check `auth().check()` before accessing user attributes. For concurrent locales, explicitly pass `locale=` because `locale()` reads shared global state.

## Escaping and trusted content

Application autoescaping defaults to enabled. Keep escaping for `{{ user.name }}`; use `|safe` and `Markup` only for HTML you control. The `markdown` filter returns an HTML `str` without sanitizing arbitrary content. Marking it safe can admit user-supplied HTML; add a sanitization policy if your product accepts external Markdown.

`json` serializes with msgspec, optionally `|json(indent=2)`, but falls back to `str(value)` when encoding fails. It is a presentation filter, not a guarantee of valid JSON for every object or a `<script>`-specific escaping mechanism. Avoid interpolating it as executable code. `dump()` exposes values as HTML and belongs in controlled diagnostics; never dump secrets. Encryption helpers do not replace authorization.

---

[Index](README.md) · [auth](../../../auth/docs/en/README.md) · [localization](../../../localization/docs/en/README.md) · [storage](../../../storage/docs/en/README.md) · [session](../../../session/docs/en/README.md)
