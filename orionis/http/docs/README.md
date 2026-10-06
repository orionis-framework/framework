# orionis.http

> `orionis.http` is Orionis' transport-independent HTTP and WebSocket layer: requests, responses, routing, middleware, payload parsing, streaming, and protocol adapters.

## Overview

The package normalizes ASGI and RSGI traffic into one `Request` API and turns Orionis `Response` objects back into server-specific messages. Its kernel resolves compiled routes, builds middleware pipelines, invokes controllers, handles failures, and serves ordinary, streaming, file, server-sent-event, and WebSocket responses.

Application code normally imports request/response types from `orionis.http`, declares routes through the `Route` facade, and implements `BaseMiddleware`. Lower-level payload and route classes are available from their defining subpackages for infrastructure code and focused tests.

## Requirements

- Python 3.14 or newer.
- An ASGI or RSGI server supported by Orionis for live traffic.
- A booted Orionis application for the `Route`, `View`, session, authentication, and other container-backed facades.
- Finite body, multipart, concurrency, and WebSocket budgets appropriate for the deployment.

## Quick start

```python
import json
from orionis.http import response

result = response.json(
    {"ok": True, "message": "ready"},
    status_code=201,
    headers={"X-Request-ID": "demo-1"},
)
assert result.getStatusCode() == 201
assert json.loads(result.getBody()) == {"ok": True, "message": "ready"}
assert result.getHeader("x-request-id") == ["demo-1"]
print(result.getMediaType())
```

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Request normalization

`Request` exposes `method`, `scheme`, `path`, `url`, `baseUrl`, `headers`, `queryParams`, `cookies`, client address data, authorization helpers, route parameters, and mutable per-request `state`. Body methods include `stream()`, `body()`, `text()`, `json()`, `xml()`, `msgpack()`, `formUrlEncoded()`, `form()`, `payload()`, and normalized dictionary `data()`.

The body stream is single-consumer unless it fits the configured buffer. Content-type-specific helpers reject mismatched media types rather than silently guessing. `wantsJson()`, `wantsHtml()`, `wantsXml()`, `accepts()`, and `isAjax()` inspect client preferences.

### Responses and delivery

`Response` stores a byte body or asynchronous byte stream, status, headers, optional media type, cookies, flash data, and an optional `BackgroundTask`. Specialized responses provide HTML, text, JSON, redirects, streams, SSE, and files. Transport adapters own ASGI/RSGI delivery; application code does not emit protocol messages itself.

### Routes and middleware

Routes accept callables, invokable controller classes, or `[Controller, "method"]`. Fluent builders add names, middleware, exclusions, prefixes, and the stateless `public()` profile. The compiler separates static and dynamic routes and supports typed parameters such as `{id:int}`. HTTP middleware receives a no-argument `call_next`; WebSocket middleware uses an equivalent connection continuation.

### Long-lived connections

`EventStreamResponse` lazily encodes `ServerSentEvent` values and disables buffering-oriented headers. `WebSocket` normalizes text, bytes, JSON, close state, and disconnect details over either server interface. A connection must be accepted before data transfer and can be rejected during the handshake.

## Module structure

| Path | Responsibility |
|---|---|
| `request.py` | Unified request metadata, content negotiation, and body decoding. |
| `responses.py`, `factory.py`, `sse.py` | Response objects, shared factory, files, streams, and SSE frames. |
| `middleware.py`, `kernel.py` | Middleware contract, pipeline execution, dispatch, and error handling. |
| `routes/` | Route declaration, groups, compilation, resolution, loading, and cache. |
| `payload/` | Bounded body streams, structured headers/cookies/query data, forms, and uploads. |
| `adapters/` | ASGI/RSGI request, response, file/range, stream, and WebSocket adapters. |
| `websocket.py`, `websocket_message.py` | Connection API, state, and normalized messages. |
| `layer/` | CORS, hosts, proxies, maintenance, rate limits, sessions, and CSRF. |
| `default/` | Framework error pages, health/static handlers, and optional auth controllers. |
| `contracts/`, `enums/`, `exceptions/` | Stable interfaces, protocol/status values, and domain errors. |

## Public API

The package root exports `Request`, `Response`, `ResponseTemplate`, `HTMLResponse`, `PlainTextResponse`, `JSONResponse`, `RedirectResponse`, `StreamingResponse`, `EventStreamResponse`, `FileResponse`, `ResponseFactory`, the shared `response`, `ServerSentEvent`, `BaseMiddleware`, `NextCallable`, `WebSocket`, `WebSocketMiddleware`, `WebSocketNext`, `WebSocketMessage`, `WebSocketMessageType`, `WebSocketState`, `WebSocketDisconnected`, and the `HttpResponse` type alias.

### `ResponseFactory`

- `view(template, **context)` returns an awaitable `PendingView`.
- `html`, `text`, and `json` build buffered typed responses.
- `redirect(url, status_code=302)` accepts only redirect status codes.
- `stream(content, ..., media_type=None)` consumes sync or async byte iterables.
- `eventStream(content, ...)` consumes strings or `ServerSentEvent` values.
- `file(path, ..., filename=None, chunk_size=65536)` streams a regular file.
- `download(path, filename=None, ...)` adds attachment disposition.
- `noContent(status_code=204)` and `make(...)` cover empty and generic responses.

### Response mutation

Use `addHeader`, `setHeader`, `getHeader`, `hasHeader`, `removeHeader`, `setCookie`, and `deleteCookie`. `withCookie`, `withCookies`, `withoutCookie`, `withFlash`, `withInput`, and `withErrors` return the same response for chaining. Adapters read `getBody`, `getStream`, `getRawHeaders`, status, media type, and `runBackground()`.

### Routes

`orionis.support.facades.Route` provides `get`, `post`, `put`, `patch`, `delete`, `query`, `view`, `websocket`, `hub`, `group`, `fallback`, and `auth`. Builders expose `name`, `public`, `middleware`, `withOutMiddleware`, `prefix`, and deferred `action`. These calls require the router registered in a booted application.

### Payload structures

`Headers`, `QueryParams`, and `Cookies` are read-only, case- or protocol-aware views. `FormData` preserves repeated fields and files. `UploadedFile` exposes `size`, `extension`, `read`, `chunks`, `replace`, `save`, and `close`; large uploads spill to a temporary file at the configured threshold.

## Common workflows

### Declare application routes

Place declarations in the application route files loaded as `web` or `api`. Name routes when another subsystem must generate their URLs. Group already-declared builders to inherit a prefix and middleware. Use `public()` only for endpoints that do not use cookie credentials: global host, CORS, security, and rate-limit layers still run.

### Parse client input

Prefer the helper matching the declared `Content-Type`. Use `await request.data()` when a normalized mapping is appropriate and `await request.payload()` when scalar or structured JSON/MessagePack values must be preserved. Close multipart `FormData` after use so temporary uploads are released.

### Return content

Return `response.json(...)` for APIs, an awaited view for templates, `response.redirect(...)` after state changes, and `response.noContent()` for a bodyless success. Streams must yield bytes; SSE may yield strings or typed events. Background work runs only after delivery cleanup.

### Handle WebSockets

Inspect `socket.path`, `headers`, `routeParams()`, and `state`, then call `await socket.accept()` before sends or receives. Use typed receive/send helpers, handle `WebSocketDisconnected`, and close explicitly when the handler completes. Connection middleware may reject before acceptance.

## Examples

### Add response headers and cookies

```python
from orionis.http import PlainTextResponse

result = PlainTextResponse("accepted", status_code=202)
result.setHeader("X-Mode", "demo")
result.setCookie("session_hint", "present", http_only=True, same_site="lax")
assert result.getBody() == b"accepted"
assert result.getHeader("x-mode") == ["demo"]
assert result.hasHeader("set-cookie")
print(result.getStatusCode())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Stream byte chunks

```python
import asyncio
from orionis.http import response


async def main() -> None:
    result = response.stream([b"orion", b"is"], media_type="application/octet-stream")
    chunks = [chunk async for chunk in result.getStream()]
    assert b"".join(chunks) == b"orionis"
    print(result.hasStream())


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Encode a server-sent event

```python
from orionis.http import ServerSentEvent

event = ServerSentEvent(
    event="progress",
    id="job-7",
    retry=1500,
    data="step 1\nstep 2",
)
frame = event.encode()
assert b"event: progress\n" in frame
assert b"data: step 1\ndata: step 2\n\n" in frame
print(frame.decode("utf-8"))
```

Validation: **Executed successfully** on CPython 3.14.6.

### Compile a typed route path

```python
from orionis.http.routes.route_compiler import RouteCompiler

is_static, pattern, converters = RouteCompiler.compilePath("/users/{id:int}")
assert not is_static and pattern is not None
match = pattern.fullmatch("/users/42")
assert match is not None
assert converters["id"](match.group("id")) == 42
print(pattern.pattern)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Inspect a normalized WebSocket message

```python
from orionis.http import WebSocketMessage, WebSocketMessageType

message = WebSocketMessage(type=WebSocketMessageType.TEXT, data="hello")
assert message.isText()
assert not message.isBytes()
assert message.text == "hello"
print(message.type.value)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Implement HTTP middleware

```python
from orionis.http import BaseMiddleware, Request, Response


class RequestIdMiddleware(BaseMiddleware):
    async def handle(self, request: Request, call_next) -> Response:
        result = await call_next()
        result.setHeader("X-Request-ID", request.state.request_id)
        return result
```

Validation: **Import- and syntax-validated** on CPython 3.14.6; runtime execution belongs to the booted kernel pipeline.

## Configuration

`config/http.py` builds the frozen `BootstrapHTTP` entity. Important groups and environment variables are:

| Group | Environment variables | Defaults / purpose |
|---|---|---|
| Body | `HTTP_MAX_BODY_SIZE`, `HTTP_MAX_BUFFER_SIZE`, `HTTP_MAX_CONCURRENT_REQUESTS` | 16 MiB body, 2 MiB buffer, 128 concurrent requests per worker. |
| Multipart | `HTTP_MAX_FILES`, `HTTP_MAX_FIELDS`, `HTTP_MAX_PART_SIZE`, `HTTP_MAX_FIELD_SIZE`, `HTTP_MAX_PART_HEADER_SIZE`, `HTTP_UPLOAD_MEMORY_THRESHOLD`, `HTTP_MAX_MULTIPART_MEMORY_SIZE` | Bound part counts, sizes, headers, memory, and disk spill. |
| Disconnects | `HTTP_MONITOR_DISCONNECTS` | Disabled by default; enables request cancellation on disconnect. |
| WebSocket | `WEBSOCKET_MAX_CONNECTIONS`, `WEBSOCKET_MAX_MESSAGE_SIZE`, `CORS_ALLOW_ORIGINS` | 128 connections, 1 MiB messages, same-origin policy unless configured. |
| Proxies/hosts | `TRUSTED_PROXIES`, `ALLOWED_HOSTS` | Trust localhost proxy by default; an empty host list allows all hosts. |
| Rate limit | `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, `RATE_LIMIT_STORE`, `RATE_LIMIT_MAX_KEYS`, `RATE_LIMIT_MAX_EVENTS`, `RATE_LIMIT_REDIS_PREFIX`, `RATE_LIMIT_REDIS_TIMEOUT` | Disabled; 100 requests per 60 seconds when enabled; memory or Redis storage. |
| Redis connection | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | `127.0.0.1`, port 6379, database 0, no password; shared connection defaults. |
| CORS | `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `CORS_EXPOSE_HEADERS`, `CORS_ALLOW_CREDENTIALS`, `CORS_MAX_AGE` | Explicit cross-origin policy; credentials disabled; 600-second preflight age. |
| CSRF | `CSRF_ENABLED`, `CSRF_TOKEN_LENGTH`, `CSRF_SESSION_KEY`, `CSRF_XSRF_COOKIE`, `CSRF_COOKIE_NAME`, `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_SAME_SITE`, `CSRF_COOKIE_PATH`, `CSRF_COOKIE_DOMAIN` | Enabled for stateful web routes; 32-byte tokens and lax cookie policy. |

MCP and WebSocket read `CORS_ALLOW_ORIGINS` directly by default. To use different allowlists, change the environment key in the corresponding application configuration or supply explicit origins. Values are not automatically filtered; MCP rejects wildcards.

`HTTPRateLimit.rate_limit_redis` accepts a `Redis` entity or a dictionary with `endpoint`, `port`, `db`, and `password`. These fields are passed directly to the lazy Redis client without assembling a URL. Real Redis integration tests require `ORIONIS_HTTP_REDIS_HOST`; optional `ORIONIS_HTTP_REDIS_PORT`, `ORIONIS_HTTP_REDIS_DB`, and `ORIONIS_HTTP_REDIS_PASSWORD` select the test connection.

## Integration with Orionis

The foundation application boots `RouterProvider`, loads `routes/web.py` and `routes/api.py`, compiles and optionally caches their declarations, then gives the result to `KernelHTTP`. The kernel resolves controllers and middleware through the container, injects validated parameters, uses session/auth services for stateful routes, and delegates failures to the default response service.

The view, validation, session, authentication, background-task, realtime hub, cache, logging, and failure modules all meet at this boundary. ASGI and RSGI adapters intentionally share request and response semantics so controllers remain server-independent.

## Errors and edge cases

- Invalid response status codes, headers, cookies, redirect codes, event fields, or stream chunks raise `TypeError` or `ValueError` early.
- A consumed unbuffered body cannot be read a second time; payloads exceeding configured budgets are rejected.
- `json`, XML, MessagePack, form, and multipart helpers reject unsupported or malformed content.
- Duplicate static routes, structurally colliding dynamic routes, duplicate route names for different paths, a second fallback, and unassigned actions fail during registration or compilation.
- Route parameters that do not satisfy their converter do not match; method mismatches are distinct from missing routes.
- File responses require an existing regular file and support range/conditional delivery through adapters.
- SSE fields forbid newline injection in `event` and `id`; retry must be a non-negative integer.
- WebSocket operations enforce connection state, message-size limits, origin policy, and connection capacity; peer closure raises `WebSocketDisconnected` where appropriate.
- Forwarded headers affect request identity only when the immediate peer is configured as trusted.

## Performance and concurrency

Body size and buffering limits are enforced while reading, and multipart parsing is streaming with bounded field/file counts. Oversized uploads can move to disk, so tune both memory and temporary-storage capacity. The per-worker request and WebSocket gates reject excess work immediately instead of forming an unbounded queue.

Static routes use dictionary lookup; dynamic routes are precompiled, scored by specificity, and indexed for resolution. `ResponseTemplate` reuses immutable encoded bodies and headers while returning independent mutable responses. Streaming, files, and SSE are consumed lazily and propagate cancellation/cleanup. Synchronous iterables may require executor work; never block the event loop inside application generators or middleware.

## Compatibility

Orionis declares Python 3.14+. The public request/response layer supports both ASGI and RSGI adapters, HTTP/1.x metadata, and server-dependent HTTP/2 metadata when supplied. WebSocket close-detail support varies by server interface and is exposed through `supportsCloseDetails`. JSON uses UTF-8 and handles common Python value types; MessagePack input depends on the installed Orionis dependency set.

## Verification notes

Validation used CPython 3.14.6. Package exports, request parsing, response families, route declaration/compilation/resolution, middleware pipelines, configuration entities, security layers, ASGI/RSGI adapters, WebSocket/SSE behavior, and integrations were inspected. All **902** tests under `tests/http` passed through the Orionis runner. Five standalone examples executed successfully; the middleware definition was import- and syntax-validated because invocation is owned by the booted kernel.
