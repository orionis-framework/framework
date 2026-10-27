# Request lifecycle and controllers

A request enters through an ASGI or RSGI adapter. The kernel applies global policies, resolves a compiled route, opens a container scope and builds the appropriate pipeline. The controller works with `Request`, injected services and server-independent responses. Completion persists the session when applicable, sends the response and releases bodies, uploads and scoped services.

## A read controller

```python
from orionis.http import Request, Response, response
from orionis.http.base.controller import BaseController

class CatalogController(BaseController):
    async def show(self, request: Request) -> Response:
        product_id = request.routeParam("product_id")
        return response.json({"id": product_id, "currency": "USD"})
```

In `routes/api.py`, register `Route.get("/products/{product_id:int}", [CatalogController, "show"])`, importing `Route` from `orionis.support.facades`. The class must be importable from a real application module. `BaseController` is an empty marker: it provides no authorization, validation or ORM helpers. Those responsibilities belong to services.

You can also register a function or an invokable class implementing `__call__`. Complete a deferred declaration with `Route.get("/products").action(CatalogController, "show")` before route compilation. The handler and its type information are inspected at boot; controller dependencies are constructed through the container.

## Choosing web or API

The loader imports `routes/web.py` first and `routes/api.py` second; location establishes the route kind. Web routes include sessions, CSRF and session identity resolution. API routes resolve token identity without automatically adding browser state. Identity resolution permits guests; require authentication explicitly to protect resources.

`public()` selects the stateless HTTP profile and removes session, CSRF and identity layers. Use it for endpoints that do not need cookie credentials or the current identity. Global policies still apply. It does not replace an authorization decision.

## Asynchronous work, scopes and failures

Use `async def` for I/O and await asynchronous APIs. Support for synchronous handlers does not make a blocking call inside an asynchronous controller safe for the event loop. Delegate long synchronous I/O or CPU work to appropriate services.

Requests and identities live in a scope. Do not retain `Request`, session or authentication context in singletons or globals. The kernel preloads and reuses middleware instances: keep per-request data in local variables or `request.state`.

Each application and HTTP kernel belongs to one worker event loop; do not share them across threads or event loops. The kernel enforces `http.body_limits.max_concurrent_requests` across ASGI and RSGI requests without blocking the loop. A request retains its slot through response delivery and resource cleanup, including cancellation. Excess requests receive `503` with `Retry-After: 1` before another request scope is allocated.

Framework handlers convert validation and authentication exceptions. An exception after streaming headers have been sent cannot replace the HTTP status already delivered. Arrange preparation work to fail before returning a stream.

## Evidence and next steps

Read [routing](routing.md), [middleware](middleware-and-security.md) and [failures](../../../failure/docs/en/README.md). Implementation: [kernel](../../kernel.py), [loader](../../routes/loader.py), [BaseController](../../base/controller.py). Tests: [kernel](../../../../tests/http/test_kernel.py), [request resources](../../../../tests/http/test_execution_resources.py), [handler plans](../../../../tests/http/test_handler_plan_warmup.py).
