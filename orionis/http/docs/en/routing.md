# Routes, parameters and groups

Declare routes at boot, usually in `routes/web.py` or `routes/api.py`. The `Route` facade requires a router registered in the application. Keep handlers and middleware classes in importable modules so cached routes can reconstruct them.

## Building a small API

```python
from orionis.http import Request, response
from orionis.support.facades import Route

async def show_product(request: Request):
    return response.json({"id": request.routeParam("product_id")})

async def create_product():
    return response.json({"created": True}, status_code=201)

Route.group(prefix="/catalog", routes=[
    Route.get("/products/{product_id:int}", show_product).name("products.show"),
    Route.post("/products", create_product).name("products.create"),
])
```

The read URL is `/catalog/products/42`. A group takes already registered routes; it is neither a context manager nor a decorator. Include other `RouteGroup` objects to nest prefixes. `middleware`, `without_middleware` and `public` are group options; an explicit route-level `public` setting takes precedence over an inherited value. An empty group does not configure later declarations.

## Converting parameters

| Syntax | Value and restriction |
|---|---|
| `{name}` or `{name:str}` | Nonempty text without `/`. |
| `{name:slug}` | Lowercase ASCII letters, digits and hyphens. |
| `{name:int}` | Digits converted to `int`; negative signs do not match. |
| `{name:uuid}` | Canonical UUID converted to `uuid.UUID`. |

`request.routeParam("name")` returns one value and `routeParams()` returns the mapping. A value outside its pattern does not match; this is separate from body validation. The current registry has no `float`, `path` or optional parameter converters.

## Actions, names and middleware

Available helpers are `get`, `post`, `put`, `patch`, `delete` and `query`. `query` declares the HTTP `QUERY` method; it does not append URL query parameters. `view(path, template)` creates a GET template route. `websocket` and `hub` register connections independently of HTTP routes.

An action may be a function, an invokable class or `[Controller, "method"]`. Builders support `.name(...)`, `.prefix(...)`, `.middleware(...)`, `.withOutMiddleware(...)` and `.public()`. Preserve the internal capital in `withOutMiddleware`; the group option is `without_middleware`.

```python
from orionis.auth.middleware import AuthenticateTokenMiddleware

Route.get("/private/product/{product_id:int}", show_product).middleware(AuthenticateTokenMiddleware)
```

Route names support identification and URL generation by services that consume the router.

## Conflicts, fallback and caching

Static routes use direct lookup; dynamic paths are compiled and ordered by specificity. Static conflicts, ambiguous dynamic structures, incompatible names and unfinished actions fail during registration or compilation. Only one fallback is allowed, using `Route.fallback(handler)`. A method mismatch is handled separately from a missing path.

The default GET favicon, robots and sitemap routes can be replaced by declaring the same path. Do not rely on overwriting ordinary routes. In compiled mode, keep classes and functions importable by name; lambdas and local classes are not a portable cache contract. The cache carries a version and rejects incompatible data.

Evidence: [router](../../routes/router.py), [builder](../../routes/fluent.py), [converters](../../routes/params_types.py), [compiler](../../routes/route_compiler.py), [cache](../../routes/route_cache.py). Tests: [nesting](../../../../tests/http/routes/test_nested_routing.py), [runtime](../../../../tests/http/routes/test_routing_runtime.py), [collisions](../../../../tests/http/routes/test_route_compiler.py). Continue with [input](requests-and-validation.md).
