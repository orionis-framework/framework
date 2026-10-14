# Responses, cookies and downloads

Import `response` from `orionis.http`. It is a shared factory that constructs an independent response on each call. Return responses from controllers; adapters handle headers and ASGI/RSGI delivery.

## Choosing a representation

```python
import json
from orionis.http import response

result = response.json({"id": 7, "status": "created"}, status_code=201)
result.setHeader("X-Request-ID", "docs-example")
assert result.getStatusCode() == 201
assert json.loads(result.getBody()) == {"id": 7, "status": "created"}
assert result.getHeader("x-request-id") == ["docs-example"]
```

`html()` and `text()` accept text or bytes. `json()` serializes application values and offers options including `indent`, `ensure_ascii` and `default`. `make()` constructs a generic response; set an explicit media type when needed. `noContent()` defaults to 204. HTML responses do not sanitize untrusted HTML: escape external data through the template engine.

For a template, use `return await response.view("catalog/index", products=products)` inside your handler; `products` must come from your service. `view()` returns a `PendingView`, so it is not interchangeable with a constructed `Response` until rendering is awaited. See [views](../../../view/docs/en/README.md).

## Redirecting with form state

```python
from orionis.http import response

result = (
    response.redirect("/settings", status_code=303)
    .withFlash("notice", "Preferences saved")
    .withInput({"theme": "dark"})
)
assert result.getStatusCode() == 303
```

The web application applies this data to its session. `withErrors()` accepts normalizable errors. Without session middleware there is no persistent flash lifecycle. Redirect destinations must be trusted; `redirect` does not replace origin checks for user-supplied URLs.

## Headers and cookies

`setHeader()` replaces a header's values; `addHeader()` appends one. `getHeader()` returns a list or `None`; lookups ignore case. Do not insert newlines in names or values. `withCookie()` supports chaining; `setCookie()` returns `None`.

```python
from orionis.http import response

result = response.text("saved").withCookie(
    "theme", "dark", secure=True, http_only=True, same_site="lax", max_age=3600,
)
result.deleteCookie("obsolete", path="/")
assert result.hasHeader("set-cookie")
```

Delete a cookie using the same `path` and `domain` used to create it. `Secure`, `HttpOnly`, `SameSite` and `Partitioned` control emitted attributes; browser acceptance is client-dependent. Use [sessions](../../../session/docs/en/README.md) for sensitive application state stored on the server.

## Files and safe reuse

`response.file(path, media_type=..., filename=...)` verifies an existing regular file and delivers it as a stream. `download(path, filename=...)` adds attachment disposition. Resolve paths from authorized identifiers rather than arbitrary client paths. Adapters implement conditional and range delivery; consult their tests before depending on a specific case. A file can disappear between construction and reading.

`ResponseTemplate` retains encoded content and base headers and creates independent responses with `make()`. Do not reuse one mutable response across requests. `background` work runs after delivery and cleanup; it is not a durable queue and does not guarantee execution after process failure.


```python
from orionis.http import ResponseTemplate

template = ResponseTemplate("ready", headers={"X-Service": "catalog"}, media_type="text/plain")
first = template.make()
second = template.make()
first.setHeader("X-Request-ID", "one")
assert not second.hasHeader("X-Request-ID")
assert first.getBody() == second.getBody() == b"ready"
```

Evidence: [factory](../../factory.py), [responses](../../responses.py), [files and ranges](../../adapters/response/files.py). Tests: [responses](../../../../tests/http/test_response.py), [transport](../../../../tests/http/adapters/test_response_transport.py), [reuse](../../../../tests/http/test_response_performance.py). Continue with [streaming](streaming-and-sse.md).
