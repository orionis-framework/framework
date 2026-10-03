# WebSocket connections and streaming responses

Orionis dispatches WebSocket connections through `Application` and `KernelHTTP`
under ASGI (`scope["type"] == "websocket"`) and Granian RSGI (`scope.proto == "ws"`).
Register a connection handler in the usual route files:

```python
from orionis.http import WebSocket
from orionis.support.facades.router import Route

async def echo(socket: WebSocket, room: int) -> None:
    await socket.accept()
    async for message in socket:
        if message.isText():
            await socket.sendText(message.text)
        elif message.isBytes():
            await socket.sendBytes(message.bytes)

Route.websocket("/rooms/{room:int}", echo).name("rooms.socket")
```

Functions, `[Controller, "method"]` and invokable controllers are supported.
The existing route compiler, converted parameters, names, grouping and route
cache are reused. HTTP GET and WebSocket routes may share a path; connection
routes do not appear in HTTP `Allow` or `OPTIONS` discovery. HTTP fallback
handlers are never called for unmatched WebSocket connections.

Raw WebSocket has no dependency on the optional `orionis.realtime` package.
`WebSocket` owns lifecycle and concurrency. `IWebSocketTransport` separates it
from `ASGIWebSocketTransport` and `RSGIWebSocketTransport`, which normalize
server events and operations. Custom transports can implement this same contract.

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

Import `WebSocket`, `WebSocketMessage`, `WebSocketMessageType`, `WebSocketState`,
`WebSocketDisconnected`, `WebSocketMiddleware` and `WebSocketNext` from
`orionis.http`. The constructor is normally owned by the
kernel; applications receive the scoped object through a type annotation.

| Member | Behavior |
|---|---|
| `path`, `headers` | Handshake metadata. |
| `state` | Mutable `SimpleNamespace` belonging to this connection. |
| `connectionState` | `CONNECTING`, `CONNECTED`, `CLOSING` or `CLOSED`. |
| `routeParams()` | Mutable converted path parameters belonging to this connection. |
| `accepted`, `closed` | Explicit handshake and terminal-state indicators. |
| `await accept(*, subprotocol=None, headers=None)` | Accept once, with supported handshake options. |
| `await receive()` | Receive one immutable `WebSocketMessage`, including one terminal disconnect event. |
| `await receiveText()` / `receiveBytes()` | Receive the expected kind; a mismatched kind raises `TypeError`. |
| `await sendText(data)` / `sendBytes(data)` | Send the explicit message kind and await network backpressure. |
| `await send(data)` | Send text/binary while awaiting transport delivery; sends and closure are serialized. |
| `await receiveJson()` | Decode a text or binary JSON message through msgspec. |
| `await sendJson(data)` | Serialize a JSON value and send UTF-8 text. |
| `await reject(status_code=403)` | Reject before acceptance; repeated rejection is harmless. |
| `await close(code=1000, reason="")` | Close or reject an unaccepted handshake; repeated closure is harmless. |
| `supportsCloseDetails` | Whether the transport supports custom close-frame code/reason. |
| `async for message in socket` | Iterate complete data messages; stop on disconnect. |

`WebSocketMessage` is a frozen, slotted, keyword-only record containing `type`,
`data`, `code` and `reason`. It retains the original payload without copying it.
Use `isText()`, `isBytes()`, `isDisconnect()`, `.text` and `.bytes` to inspect it.
The typed accessors raise `TypeError` for the wrong kind. `receive()` delivers
the disconnect event once; subsequent reads and writes raise
`WebSocketDisconnected`. The typed receive helpers also raise this exception
when a peer disconnects, preserving its available `code` and `reason`.

Messaging requires completed acceptance. Concurrent receivers fail immediately
with `RuntimeError`; there is no reader queue. Sends, acceptance and closure share
one connection lock and await the server directly. Cancelling a reader releases
its lock and leaves the socket usable. Cancelling a writer while it waits for
the lock affects only that caller. Cancelling an active network write or
acceptance leaves `CLOSING`: its delivery is uncertain, so further messaging is
rejected and the owner must close the connection. Cancellation always propagates.
Repeated close calls emit no duplicate frames, including after failed closure.
Server errors other than explicit transport disconnection remain visible.

The kernel treats a disconnect as normal completion. Other
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

ASGI supports a client-offered subprotocol and acceptance headers on servers
advertising HTTP specification 2.1 or later. Headers are lowercase, cannot contain
CR/LF, and cannot include `sec-websocket-protocol` or pseudo-headers. Use the
`subprotocol` argument for negotiation. Missing `asgi.spec_version` means 2.0;
requesting headers there raises `NotImplementedError` before consuming the
handshake. Close reasons are sent from specification 2.3 onward; older servers
receive the code only. Disconnect reasons are retained whenever supplied.

Granian RSGI's public API exposes
`close(status)` for HTTP handshake rejection and default connection closure,
not WebSocket close frame codes/reasons; a custom code/reason under RSGI raises
`NotImplementedError`. Oversized RSGI messages close through that default API
while reporting 1009 locally. ASGI rejection returns HTTP 403 unless the server
advertises the `websocket.http.response` denial extension; the extension permits
the requested status. RSGI accepts the requested HTTP rejection status.
Granian 2.8.4 `accept()` takes no arguments. Requesting a subprotocol or nonempty
acceptance headers therefore raises `NotImplementedError` before acceptance.
Its message kinds 0/1/2 map to disconnect/bytes/text; close events have no peer
code or reason, represented by 1006/`None`. Explicit `ProtocolClosed` and network
errors become `WebSocketDisconnected` with the original cause; `ProtocolError`
is propagated as a server error rather than silently hidden.

These differences follow the primary [ASGI HTTP/WebSocket specification](https://asgi.readthedocs.io/en/latest/specs/www.html)
and [Granian RSGI specification](https://github.com/emmett-framework/granian/blob/v2.8.4/docs/spec/RSGI.md).

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

`tests/http/test_websocket_transport.py` adds deterministic send barriers and
actual Granian exception classes to verify serialization, backpressure,
cancellation, immutable messages, handshake negotiation, unsupported features,
malformed events and close/read races. `test_websocket_shutdown.py` checks
connection task joining and scope cleanup on application shutdown.

Executed command: `.venv/Scripts/python.exe reactor test --start-dir=tests/http
--file-pattern=test_websocket*.py --verbosity=0`: **47 passed**, including
WebSocket status and shutdown cases. The raw production modules pass targeted
Ruff and Pyright checks with zero diagnostics. Installed Granian 2.8.4 runtime
signatures and packaged type stubs were inspected directly. These tests use
deterministic protocol doubles; they do not establish throughput or soak limits.

Migration: the kernel-owned constructor now takes `(transport, adapter, *,
params=None, max_message_size=1048576)`. Existing handlers that expected `str` or
`bytes` from `receive()` must select `receiveText()`/`receiveBytes()` or read
`message.data`. `send(str | bytes)` remains available.
