# WebSocket connections and streaming responses

Orionis dispatches WebSocket connections through `Application` and `KernelHTTP`
under ASGI (`scope["type"] == "websocket"`) and Granian RSGI (`scope.proto == "ws"`).
Register a connection handler in the usual route files:

```python
from orionis.http import WebSocket, WebSocketDisconnected
from orionis.support.facades.router import Route

async def echo(socket: WebSocket, room: int) -> None:
    await socket.accept()
    try:
        while True:
            await socket.send(await socket.receive())
    except WebSocketDisconnected:
        return

Route.websocket("/rooms/{room:int}", echo).name("rooms.socket")
```

Functions, `[Controller, "method"]` and invokable controllers are supported.
The existing route compiler, converted parameters, names, grouping and route
cache are reused. HTTP GET and WebSocket routes may share a path; connection
routes do not appear in HTTP `Allow` or `OPTIONS` discovery. HTTP fallback
handlers are never called for unmatched WebSocket connections.

## Connection lifecycle and dependencies

Every admitted connection opens a new container scope which remains active until
the handler and connection middleware finish, including closure and cleanup.
The current `WebSocket` is bound in that scope. Constructor and handler injection
use the same connection object and scoped services; separate connections have
independent instances. Handler return values must be `None`.

The handshake applies proxy normalization, maintenance, configured security
validation, the configured global rate limiter and an explicit browser Origin
guard. An Origin is allowed when it matches the handshake scheme/Host or an
entry in `http.websocket.allow_origins`; `"*"` explicitly allows every Origin.
Clients which do not send Origin are allowed by this guard. Origin validation
does not authenticate a client. Validate credentials and permissions before
calling `accept()`.

HTTP application middleware, automatic sessions, CSRF and identity restoration
are omitted for connection routes. They require HTTP request/response and cookie
semantics. Explicit connection middleware subclasses `WebSocketMiddleware`:

```python
from orionis.http import WebSocket, WebSocketMiddleware, WebSocketNext

class SocketGuard(WebSocketMiddleware):
    __slots__ = ()

    async def handle(self, socket: WebSocket, call_next: WebSocketNext) -> None:
        if socket.headers.get("x-access") != "expected-application-credential":
            await socket.reject(status_code=401)
            return
        await call_next()

Route.websocket("/rooms/{room:int}", echo).middleware(SocketGuard)
```

Connection middleware is constructed through DI for every connection rather
than cached at kernel boot. Continuations may be called only once. Attaching
HTTP middleware to a connection route, or connection middleware to an HTTP
route, fails during route compilation.

## Public connection API

Import `WebSocket`, `WebSocketDisconnected`, `WebSocketMiddleware` and
`WebSocketNext` from `orionis.http`. The constructor is normally owned by the
kernel; applications receive the scoped object through a type annotation.

| Member | Behavior |
|---|---|
| `path`, `headers` | Handshake metadata. |
| `state` | Mutable `SimpleNamespace` belonging to this connection. |
| `routeParams()` | Mutable converted path parameters belonging to this connection. |
| `accepted`, `closed` | Explicit handshake and terminal-state indicators. |
| `await accept()` | Accept once; messaging before acceptance raises `RuntimeError`. |
| `await receive()` | Receive a complete `str` or `bytes`; one concurrent receiver is permitted. |
| `await send(data)` | Send text/binary while awaiting transport delivery; sends and closure are serialized. |
| `await receiveJson()` | Decode a text or binary JSON message through msgspec. |
| `await sendJson(data)` | Serialize a JSON value and send UTF-8 text. |
| `await reject(status_code=403)` | Reject before acceptance; repeated rejection is harmless. |
| `await close(code=1000, reason="")` | Close or reject an unaccepted handshake; repeated closure is harmless. |

A disconnect raises `WebSocketDisconnected` with `code` and `reason` attributes
when available. The kernel treats a disconnect as normal completion. Other
application errors propagate to the server after ASGI closure with code 1011.
The kernel closes a connection when its handler returns and releases its scope
and admission slot on completion, exception or cancellation. Client disconnects
are observed through receive/send; idle handlers must retain a receive loop or
rely on server cancellation/timeouts. HTTP disconnect watchers are not attached
to WebSocket protocols.

## Operational limits and protocol differences

```python
from orionis.foundation.config.http import HTTP, HTTPWebSocket

http = HTTP(websocket=HTTPWebSocket(
    max_connections=128,
    max_message_size=1024 * 1024,
    allow_origins=("https://client.example",),
))
```

Those are the default connection/message limits. Admission is bounded per
kernel and thread-safe; rejected excess connections do not allocate another DI
scope. Connection limits are separate from HTTP request admission. Global
limits across worker processes require server/deployment controls.

Inbound text is measured in UTF-8 bytes; binary messages use their byte length.
Oversized messages terminate the connection and raise
`WebSocketDisconnected(code=1009)`. The check occurs after the server supplies
one complete message, so it cannot cap buffers inside the protocol server.
Configure server-level frame/message and connection limits as well. No outgoing
application queue is retained and each send is awaited.

ASGI can transmit close frame codes/reasons. Granian RSGI's public API exposes
`close(status)` for HTTP handshake rejection and default connection closure,
not WebSocket close frame codes/reasons; a custom code/reason under RSGI raises
`NotImplementedError`. Oversized RSGI messages close through that default API
while reporting 1009 locally. ASGI rejection returns HTTP 403 unless the server
advertises the `websocket.http.response` denial extension; the extension permits
the requested status. RSGI accepts the requested HTTP rejection status.
Subprotocol negotiation and custom acceptance headers are not exposed by the
shared API because Granian RSGI `accept()` does not accept those parameters.

These differences follow the primary [ASGI HTTP/WebSocket specification](https://asgi.readthedocs.io/en/latest/specs/www.html)
and [Granian RSGI specification](https://github.com/emmett-framework/granian/blob/master/docs/spec/RSGI.md).

## Existing HTTP response streaming

`StreamingResponse` and `response.stream(...)` already stream async or sync byte
iterables under both ASGI and RSGI without materializing a response body. Each
chunk is sent before requesting the next chunk. Async iterators are closed in
the transport adapter's `finally` block when delivery fails or is cancelled.
`FileResponse` sends bounded 64 KiB reads under ASGI and delegates file/range
output to Granian under RSGI. Background tasks run after successful delivery,
inside the request scope.

Synchronous iterable advancement still runs on the event-loop thread; use async
generators or explicitly offload blocking work. Awaiting RSGI HTTP stream sends
does not independently guarantee a server memory cap: buffer behavior belongs
to Granian. Streaming output is therefore an implemented feature, with explicit
server/deployment limits, rather than a newly missing feature.

## Executed verification

`tests/http/test_websocket.py` covers transport state, text/binary/JSON,
disconnects, UTF-8 limits, real container injection and scoped isolation,
controllers, middleware authorization, single-use continuations, capacity,
Origin guarding, failure and cancellation cleanup. Foundation dispatch tests
verify that both WebSocket protocols preserve their original callbacks while
bypassing HTTP disconnect watchers.

`python -m benchmarks.runtime_load --seconds 0.1 --concurrency 1 --scenarios plain`
also performs real TCP probes against Granian ASGI and RSGI: HTTP 101 and its
accept digest, masked text/binary echo and the server close frame. Results carry
`websocket_probe` fields. This is protocol integration evidence, not a WebSocket
throughput or long-duration soak certification.
