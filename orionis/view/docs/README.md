# orionis.view

> `orionis.view` renders asynchronous Jinja2 templates as Orionis HTML responses with framework-aware globals, filters, flash data, and response mutation.

## Overview

`orionis.view` renders server-side HTML with an asynchronous Jinja2 environment integrated with Orionis routing, sessions, localization, storage, security, and HTTP responses. Controllers normally use the `View` facade; the factory returns a lazy `PendingView` that can collect flash data and response mutations before rendering.

Templates may be addressed with dot notation such as `users.profile` or with relative paths such as `users/profile.html`. Rendering always uses Jinja2's async path and produces an Orionis `HTMLResponse` with `X-Orionis-Render: SSR`.

## Requirements

- Python 3.14 or newer.
- At least one configured template directory; the default is `resources/views` relative to the application base path.
- A bootstrapped Orionis application for the facade and service-backed template globals.
- Jinja2, MarkupSafe, Markdown, and msgspec as installed by the project dependencies.

## Quick start

Create `resources/views/users/profile.html`:

```html
<!doctype html>
<h1>{{ user.name }}</h1>
<a href="{{ await route('users.edit', id=user.id) }}">Edit</a>
```

Return it from an async controller:

```python
from orionis.support.facades import View

async def profile(user):
    return await View.make("users.profile", user=user)
```

## Core concepts

### Environment, engine, and factory

`ViewEnvironment` owns the single configured Jinja2 `Environment`, including loaders, caches, globals, filters, tests, and extensions. `Jinja2Engine` normalizes template identifiers and renders them asynchronously. `ViewFactory.make()` creates a `PendingView` rather than rendering immediately.

`ViewServiceProvider` binds the environment, engine, and factory contracts as singletons, registers all built-ins, and pins the facade during boot.

### Deferred responses

`PendingView` is awaitable. Before awaiting it, call `withFlash()`, `withInput()`, or `withErrors()` to queue session flash data. Any callable public method on `HTMLResponse`, including `addHeader()`, `withCookie()`, and `withoutCookie()`, can also be chained; calls are recorded and replayed in order after rendering.

Submitted input is filtered so credential-like fields such as passwords are not flashed. If no session is active, queued flash data is skipped without preventing the page from rendering.

### Template loading and escaping

Configured view paths are searched in order. Relative paths resolve from the application base path. Packaged Orionis error pages remain available under the reserved `__orionis__/default/` prefix. Application templates use the configured `autoescape` value; packaged framework pages always escape expressions.

Dot notation is converted to slashes and receives `.html` when no extension exists. A name already containing `/` is treated as a path. For example, `mail.receipt` becomes `mail/receipt.html`, while `mail/receipt.j2` is retained.

## Module structure

| Path | Responsibility |
| --- | --- |
| `cache.py` | Human-readable, collision-resistant Jinja2 bytecode cache names. |
| `contracts/` | Environment, engine, and factory interfaces. |
| `engine.py` | Async Jinja2 rendering and template-name normalization. |
| `environment.py` | Loader, escaping, in-memory cache, and disk-cache setup. |
| `exceptions.py` | View exception hierarchy. |
| `extensions/csrf.py` | `{% csrf %}` Jinja statement. |
| `factory.py` | Public factory that creates pending renders. |
| `filters/` | `json` and `markdown` filters. |
| `globals/` | Application-aware template helpers. |
| `pending.py` | Awaitable render, flash queue, and response mutation queue. |
| `provider.py` | Container bindings and built-in registrations. |

## Public API

### Rendering API

- `View.make(template, **context) -> PendingView`: primary facade API after application boot.
- `ViewFactory.make(template, **context) -> PendingView`: injectable equivalent.
- `PendingView.render() -> HTMLResponse`: explicit async render; awaiting the pending object is equivalent.
- `PendingView.withFlash(key, value=None)`, `withInput(values)`, and `withErrors(errors)`: queue session flash state.
- `IViewFactory`, `IViewEngine`, and `IViewEnvironment`: contracts for application extensions and alternate implementations.

### Environment customization

- `ViewEnvironment.addGlobal(name, value)` registers a template-global value or callable.
- `addFilter(name, callback)` registers a `value | filter` operation.
- `addTest(name, callback)` registers a `value is test` predicate.
- `addExtension(extension)` registers a Jinja2 extension and wraps failures in `ViewException`.
- `getJinjaEnvironment()` returns the shared environment; external code should treat it as read-only.

### Exceptions

`ViewException` is the common base. `ViewTemplateNotFoundException` represents loader misses, `ViewRenderException` wraps rendering failures, and `ViewRouteException` reports unknown named routes or missing path parameters.

## Common workflows

### Render directly with an isolated engine

```python
import asyncio

import jinja2

from orionis.view.engine import Jinja2Engine

class Environment:
    def __init__(self) -> None:
        self.jinja = jinja2.Environment(
            loader=jinja2.DictLoader({"hello.html": "Hello {{ name }}!"}),
            enable_async=True,
            autoescape=True,
        )

    def getJinjaEnvironment(self) -> jinja2.Environment:
        return self.jinja

html = asyncio.run(Jinja2Engine(Environment()).render("hello", {"name": "Ada"}))
assert html == "Hello Ada!"
```

### Build an HTML response and queue mutations

```python
import asyncio

from orionis.view.factory import ViewFactory

class Engine:
    async def render(self, template: str, context: dict) -> str:
        return f"<h1>{context['title']}</h1>"

pending = ViewFactory(Engine()).make("pages.home", title="Welcome")
pending.addHeader("X-Page", "home").withCookie("theme", "dark")
response = asyncio.run(pending.render())

assert response.getBody() == b"<h1>Welcome</h1>"
assert response.getHeader("X-Page") == ["home"]
assert response.getHeader("X-Orionis-Render") == ["SSR"]
```

### Redisplay a failed form

```python
from orionis.view.factory import ViewFactory

class Engine:
    async def render(self, template: str, context: dict) -> str:
        return ""

pending = ViewFactory(Engine()).make("auth.login")
pending.withInput({"email": "ada@example.com", "password": "secret"})
pending.withErrors({"email": "Unknown account"})
pending.withFlash("status", "Please review the form")

assert pending._flash["_old_input"] == {"email": "ada@example.com"}
assert pending._flash["_errors"] == {"email": ["Unknown account"]}
```

## Examples

### Validate configuration

```python
from orionis.foundation.config.view import View

config = View(
    paths=["resources/views", "packages/admin/views"],
    cache_size=400,
    cache_path="storage/framework/views",
    auto_reload=False,
    autoescape=True,
)

assert config.paths[0] == "resources/views"
assert config.autoescape is True
```

### Use the built-in filters

```python
from orionis.view.filters import _filter_json, _filter_markdown

jsonify = _filter_json()
markdown = _filter_markdown()

assert jsonify({"ok": True}) == '{"ok":true}'
assert markdown("**safe**").strip() == "<p><strong>safe</strong></p>"
```

### Inspect normalization and cache keys

```python
from orionis.view.cache import OrionisBytecodeCache
from orionis.view.engine import Jinja2Engine

assert Jinja2Engine._normalisePath("users.profile") == "users/profile.html"
assert Jinja2Engine._normalisePath("partials/nav.j2") == "partials/nav.j2"

cache = OrionisBytecodeCache("storage/framework/views")
key = cache.getCacheKey("users/profile.html")
assert key.startswith("users.profile.")
assert len(key.rsplit(".", 1)[-1]) == 8
```

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `VIEW_PATHS` | `["resources/views"]` | Ordered template search directories. |
| `VIEW_CACHE_SIZE` | `400` | Compiled-template memory cache; `0` disables, `-1` is unlimited. |
| `VIEW_CACHE_PATH` | `storage/framework/views` | Disk bytecode-cache directory; use `None` in configuration to disable. |
| `APP_DEBUG` | `True` | Supplies `auto_reload`; normally disable in production. |
| `VIEW_AUTOESCAPE` | `True` | Automatic HTML escaping for application templates. |

Paths and the cache directory may be absolute; relative values resolve against the application base path. `paths` must be a non-empty list or tuple of strings, and `cache_size` must be at least `-1`.

## Integration with Orionis

The provider registers these template globals: `app`, `asset`, `secure_asset`, `auth`, `cache`, `collect`, `config`, `csrf_field`, `csrf_token`, `dump`, `encrypt`, `decrypt`, `errors`, `flash`, `framework_version`, `python_version`, `now`, `today`, `old`, `request`, `route`, `session`, `stringable`, `url`, `secure_url`, `trans`/`__`, `choice`, `locale`, and `locales`.

`auth()` returns the public `Auth` facade from `orionis.support.facades`. Read the current request's identity with `auth().user()`, or check `auth().check()` and `auth().guest()`. Guests have no user, so guard attribute access with `{% if auth().check() %}`. In authenticated layouts, `{% set user = auth().user() %}` removes the need to pass a user from each controller. The global does not cache an identity.

Many globals are asynchronous because they resolve scoped framework state. Jinja's async renderer awaits their values; explicit calls in templates may use `await` as shown in the quick start. The `json` and `markdown` filters and the `{% csrf %}` extension are installed automatically.

Named-route generation interpolates `{name}` and `{name:type}` placeholders, percent-encodes path values, and appends unused arguments as query parameters. With a request in scope, URL helpers build absolute URLs from the request; otherwise route generation can return the interpolated path.

## Errors and edge cases

- Missing templates preserve `ViewTemplateNotFoundException`; other pending-render failures are wrapped in `ViewRenderException` with the original cause.
- Jinja template errors are wrapped in `ViewRenderException` by the engine.
- Unknown chained attributes on `PendingView` raise `AttributeError`; only callable `HTMLResponse` attributes may be queued.
- Flash operations silently do nothing when no session service is available.
- `errors.first()` returns the first available message and the error bag normalizes scalar messages to lists.
- The JSON filter returns `str(value)` when msgspec cannot encode a value.
- The Markdown filter emits HTML; autoescaping rules still determine whether that string is treated as markup when inserted into a template.
- The `{% csrf %}` extension raises `ViewRenderException` if `csrf_field` is not registered.
- An unknown named route or a missing path parameter raises `ViewRouteException`.
- Jinja's default `Undefined` is permissive; a missing variable usually renders empty rather than raising.

## Performance and concurrency

The environment, engine, and factory are singletons. Jinja keeps up to `cache_size` compiled templates in memory and optionally persists bytecode to disk. Cache filenames include a readable flattened template name plus an eight-character SHA-1 digest to prevent extension/path collisions.

Template-name normalization uses a lock-protected LRU cache capped at 1,024 entries. Named-route interpolation plans are memoized; racing threads can only calculate and store the same deterministic value. Rendering is async, while the shared environment is mutated only during application boot. Register custom globals, filters, tests, and extensions during provider boot rather than during concurrent requests.

## Compatibility

The module requires Python 3.14+ and Jinja2 async rendering. Templates use Jinja2 syntax, not Python format strings. `PendingView` returns Orionis's native `HTMLResponse`, so response headers, cookies, background work, and downstream transports follow the HTTP module's contracts.

`orionis.view` has no root re-exports; use `orionis.support.facades.View` for application code or import concrete classes from their defining modules for extensions and isolated tests.

## Verification notes

This documentation was regenerated against the current source and verified with CPython 3.14.6. All 207 test methods under `tests/view` passed. The seven Python blocks are identical between languages: the six self-contained implementation examples were executed successfully, and the facade quick start was syntax-checked because it requires an application and template file.
