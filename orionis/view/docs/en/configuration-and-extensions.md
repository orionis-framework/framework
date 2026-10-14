# Configuring, extending, and diagnosing views

View renders server-side HTML with async Jinja2 and returns an Orionis response.

## Configure loading and caching

Paths are searched in order: a template in the first directory shadows the same name in later directories. The `__orionis__/default/` prefix is reserved for packaged pages and resolves before application paths. Relative search and cache paths resolve against `app.basePath`.

Jinja's template cache differs from bytecode caching: `cache_size` bounds compiled objects in memory; `cache_path` persists bytecode on disk. Setting `cache_path=None` disables only the latter. With `auto_reload` disabled, restart or rebuild the environment when deploying changes: editing a template does not force a warm process to update. Neither cache stores complete HTML responses or controls cache headers.

`Undefined` is permissive: a missing variable can render empty text. This helps optional views but can hide naming mistakes. Prepare explicit context and verify pages with populated data, empty data, and guests. Templates are trusted application code: this environment is not a sandbox for arbitrary user templates.

## Register filters, tests, and globals

A custom provider must run after View services have been registered. Add its class to the application provider registry according to Foundation configuration. This example shows the extension body; it does not automatically register the class:

```python
from orionis.container.providers.service_provider import ServiceProvider
from orionis.view.contracts.environment import IViewEnvironment


class ViewHelpersProvider(ServiceProvider):
    async def boot(self) -> None:
        environment: IViewEnvironment = await self.app.make(IViewEnvironment)
        environment.addFilter("money", lambda value: f"${value:,.2f}")
        environment.addTest("positive", lambda value: value > 0)
        environment.addGlobal("support_email", "help@example.com")
```

Use them with `{{ total | money }}`, `{% if total is positive %}`, and `{{ support_email }}`. `addGlobal`/`addFilter`/`addTest` replace existing names; avoid accidentally overriding fundamental helpers. `addExtension` accepts Jinja extensions and wraps registration failures in `ViewException`.

For an alternative engine, implement async `IViewEngine.render(template, context) -> str` and replace that binding before resolving `IViewFactory`. The factory and engine are singletons: changing a binding after resolution does not automatically rebuild existing references. Customize the environment during boot and treat it as shared read-only state during requests. Never store a user or tenant in a mutable global.


## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `VIEW_PATHS` | `["resources/views"]` | Ordered template search directories. |
| `VIEW_CACHE_SIZE` | `400` | Compiled-template memory cache; `0` disables, `-1` is unlimited. |
| `VIEW_CACHE_PATH` | `storage/framework/views` | Disk bytecode-cache directory; use `None` in configuration to disable. |
| `APP_DEBUG` | `True` | Supplies `auto_reload`; normally disable in production. |
| `VIEW_AUTOESCAPE` | `True` | Automatic HTML escaping for application templates. |

Paths and the cache directory may be absolute; relative values resolve against the application base path. `paths` must be a non-empty list or tuple of strings, and `cache_size` must be at least `-1`.



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

### Environment customization

- `ViewEnvironment.addGlobal(name, value)` registers a template-global value or callable.
- `addFilter(name, callback)` registers a `value | filter` operation.
- `addTest(name, callback)` registers a `value is test` predicate.
- `addExtension(extension)` registers a Jinja2 extension and wraps failures in `ViewException`.
- `getJinjaEnvironment()` returns the shared environment; external code should treat it as read-only.

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

## Inspect bytecode names

`OrionisBytecodeCache` uses readable names plus an eight-character digest to distinguish paths and extensions. This is a regenerable compiled cache; do not use it as business-data storage. Inspect a key without opening files:

```python
from orionis.view.cache import OrionisBytecodeCache

cache = OrionisBytecodeCache("storage/framework/views")
key = cache.getCacheKey("users/profile.html")
assert key.startswith("users.profile.")
assert len(key.rsplit(".", 1)[-1]) == 8
assert key != cache.getCacheKey("users/profile.j2")
```

## Implementation reference for extensions

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

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md) · [container](../../../container/docs/en/README.md) · [failure](../../../failure/docs/en/README.md)
