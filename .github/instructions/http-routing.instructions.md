---
name: "Orionis HTTP, Routing and Controllers"
description: "Use when working on the Orionis HTTP layer: KernelHTTP (ASGI/RSGI), route declaration and resolution, middlewares, controllers, Request and Response objects, the response factory, and validation errors turned into 422 JSON or a redirect back."
applyTo: "orionis/http/**,app/http/**,routes/web.py,routes/api.py"
---

# HTTP layer

> `orionis/http/` has **no** `docs/` folder yet, so this file plus the source are
> the reference. If you finish a chunk of work here, creating
> `orionis/http/docs/README.md` + `README.es.md` is the expected follow-up.
> Related manuals: `orionis/view/docs/`, `orionis/session/docs/`,
> `orionis/schemas/docs/`.

## Kernel

`orionis/http/kernel.py` — `KernelHTTP` serves both **ASGI** (`handleASGI`) and **RSGI**
(`handleRSGI`) on top of Granian.

- Full `__slots__`; `IKernelHTTP` declares `__slots__ = ()`.
- Handler dispatch tables (`__fn_dispatch` / `__cls_dispatch`, keyed by `id(route)`) are
  preloaded in `__preloadHandlers` at boot.
- `_MiddlewarePipeline` uses slots and a bitmask — **no closures per request**.
- `__processRequest` returns a `Response`; the transport methods send it without lambdas.
  Exceptions go to `__handleException`.
- Layers: `layer/shared/` (`cors`, `maintenance`, `proxies`, `rate_limit`, `security`),
  `layer/web/` (`csrf_token`, `start_session`), `layer/api/`, `layer/store/`.
- `__webTerminal` wraps `__requestLayer` in `try/except ValidationException` **inside**
  `StartSessionMiddleware`, because flash data is only persisted after `call_next()`.

Performance rules for this folder: precompute in `__init__`/`boot()`, never allocate per
request what can be built once, iterate headers with `__iter__` instead of `.items()`,
and keep `getScope()` returning the original dict by identity when nothing overrode it.

## Routing

```python
from app.http.controllers.auth.login_controller import LoginController
from orionis.support.facades.router import Route

Route.get("/", [HomeController, "index"])
Route.post("/login", [LoginController, "login"]).name("login")
```

- Action is `[Class, "method"]` or a callable. Fluent API: `.name()`, `.middleware()`,
  `.withOutMiddleware()`. Groups: `Router.group(prefix=..., middleware=...,
  without_middleware=...)`.
- Parameters: `/users/{id}` and `/users/{id:int}` (types in `routes/params_types.py`).
- **Hot path is only `RouteResolver.resolve`** (once per request). `router.py`,
  `fluent.py`, `route_compiler.py`, `route_cache.py` and `loader.py` are startup-only.
- Static routes are precomputed as `ResolvedRoute` in the resolver `__init__`; dynamic
  ones use a FIFO cache and extractors based on `regex.groupindex`. The global dynamic
  regex must use non-capturing groups (duplicate names break `re.compile`).
- Route middleware is always flattened with `flatten_middleware()`.
- Module-level functions in `orionis/http/routes/` are **snake_case**
  (`normalize_path`, `parse_action`, `flatten_middleware`, ...).
- When changing router signatures, update `contracts/` and
  `orionis/support/facades/router.pyi` too.

## Middleware

```python
from orionis.http import BaseMiddleware, NextCallable, Request, Response

class RequestIDMiddleware(BaseMiddleware):

    async def handle(self, request: Request, call_next: NextCallable) -> Response:
        """Attach a unique request ID and delegate to the next handler."""
        request.state.unique_id = secrets.token_hex(16)
        return await call_next()
```

`call_next` is a **no-arg async callable**. Global middleware is registered with
`app.withMiddleware(...)` in `bootstrap/app.py`. Concrete middlewares must declare
`__slots__`.

## Request

- Cached properties: `url`, `baseUrl`, `headers`, `method`, `path`, `query`, `cookies`,
  `state`.
- `await request.data()` is cached — safe to call after the container already used the
  body to validate a schema.
- Helpers: `wantsJson()`, `isAjax()`.
- Under RSGI the host comes from the `Host` header, not `scope["server"]` (using the
  latter broke same-origin redirects and session cookies).

## Response

> The module is **`orionis/http/responses.py`**, not `response.py`. `orionis/http/__init__.py`
> exports the factory instance named `response`, and a sibling submodule with the same
> name made the attribute non-deterministic. Never re-introduce that shadowing.

```python
from orionis.http import HttpResponse, response

await response.view("auth.login")             # PendingView → MUST be awaited
response.redirect("/login").withInput(data)   # real Response → must NOT be awaited
response.json(...) / .html(...) / .text(...) / .stream(...) / .file(...) / .download(...)
response.noContent() / .make(...)
```

Fluent helpers: `withCookie`, `withHeader`, `withInput`, `withErrors`, `withFlash`.
`orionis/http/types.py` defines `type HttpResponse = Response` — use it to annotate
controller return values. The kernel requires a real `Response`; returning a
`PendingView` raises `TypeError: Route handler must return a Response object`.

## Controllers

```python
from typing import Any
from app.http.schemas.auth.login import LoginSchema
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.request import Request

class LoginController(BaseController):

    async def index(self) -> HttpResponse:
        """Return the login page response."""
        return await response.view("auth.login")

    async def login(self, request: Request, payload: LoginSchema) -> HttpResponse:
        """Handle the login form submission."""
        credentials: dict[str, Any] = await request.data()
        return (
            response.redirect("/login")
                .withInput(credentials)
                .withFlash("success", "Credentials received.")
        )
```

The container injects `request` (from the scope) and `payload` (validated because the
annotation is a `Schema` subclass) — never validate manually in the controller.

## Validation and errors

`orionis/http/validation.py`:

- `validation_response(exc, request, responses)` — JSON/AJAX request → **422** with
  `exc.error()` (`{"message": ..., "errors": {...}}`); browser → `RedirectResponse(302)`
  to `previous_url()` plus `.withErrors(exc.errors)` and `.withInput(await request.data())`.
- `previous_url(request)` order: session `getPreviousUrl()` → same-origin `Referer` →
  the request URL itself. It never falls back to `/`.
- API routes force `expects_json=True` for `ValidationException`.
- `CSRFTokenMismatchException` maps to **419 PAGE_EXPIRED**.
- `DefaultResponses.error(...)` takes `content`, **not** `description`, and it is
  required.
