# WebSocket connections

`WebSocket` exposes the same API over ASGI and RSGI. Register a handler with `Route.websocket(path, action)`; the connection has converted parameters, headers and its own state. An HTTP GET route at the same path does not replace a WebSocket route.

## Generate an invokable handler

```shell
python -B reactor make:realtime-socket chat
```

This creates `app/realtime/sockets/chat_socket.py` with `ChatSocket`, an asynchronous handler that echoes text messages and closes the connection on completion. Register it explicitly in your WebSocket routes:

```python
from app.realtime.sockets.chat_socket import ChatSocket
from orionis.support.facades import Route

Route.websocket("/ws/chat", ChatSocket)
```

Names can include nested directories; the generator respects `app_realtime_sockets` and never overwrites existing files. For typed RPC, generate a [hub](../../../realtime/docs/en/hubs-and-methods.md) instead of a text socket.

## A JSON echo

```python
from orionis.http import WebSocket, WebSocketDisconnected

async def echo(socket: WebSocket) -> None:
    await socket.accept()
    try:
        while True:
            value = await socket.receiveJson()
            await socket.sendJson({"echo": value})
    except WebSocketDisconnected:
        return
    finally:
        await socket.close()
```

In a route file, import `Route` from `orionis.support.facades` and declare `Route.websocket("/ws/echo", echo)`. The handler needs an upgrade-capable server; importing it opens no connections. `receiveJson()` expects JSON text messages. For binary data use `receiveBytes()`/`sendBytes()`, for text use `receiveText()`/`sendText()`, or call `receive()` to inspect a `WebSocketMessage` and its type.

## State and handshake

Call `accept()` before sending or receiving application data. Its keyword arguments can select a subprotocol and handshake headers. Reject before acceptance using `await socket.reject(status_code=403)`. After acceptance, terminate with `close(code=1000, reason="...")` rather than an HTTP response.

`accepted`, `closed` and `connectionState` expose state. `supportsCloseDetails` identifies transport differences in reporting close reasons and codes. Invalid-state operations and unexpected message kinds raise errors; do not ignore them and continue writing to a closed socket.

## Middleware and authentication

WebSocket middleware extends `WebSocketMiddleware` and receives the connection and a no-argument continuation. Do not attach HTTP response middleware to a socket route. Check access before `accept`; an allowed origin does not establish identity. The kernel creates a connection context and hubs can use that identity. Long-lived connection state does not replace per-operation authorization when your application needs it.

`socket.routeParams()` retains route conversions; `socket.headers` and `.state` are synchronous. This API has no HTTP form body to read. For typed RPC, groups and correlated results, continue with [Realtime](../../../realtime/docs/en/README.md).

## Limits and disconnects

Bootstrap defaults are 128 connections per worker through `WEBSOCKET_MAX_CONNECTIONS` and 1 MiB through `WEBSOCKET_MAX_MESSAGE_SIZE`. The origin policy reads `CORS_ALLOW_ORIGINS`; without an explicit list WebSocket uses same-origin checks. MCP applies different rules. The kernel rejects excess capacity and cancels connections at shutdown.

Handle `WebSocketDisconnected`, cancel handler-owned work and await cleanup in `finally`. Close details vary by server; do not base security decisions on peer-supplied reason text. Connection limits multiply across workers and do not provide distributed admission control.

Evidence: [WebSocket](../../websocket.py), [middleware](../../websocket_middleware.py), [adapters](../../adapters/websocket/asgi.py). Tests: [API](../../../../tests/http/test_websocket.py), [transport](../../../../tests/http/test_websocket_transport.py), [shutdown](../../../../tests/http/test_websocket_shutdown.py). See [security](middleware-and-security.md).
