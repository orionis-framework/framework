# Streaming and server-sent events

Streaming avoids assembling an entire body in memory and delivers results as they become available. Use it for exports or progress. It does not remove data-production costs, connection capacity requirements or upstream limits.

## Delivering bytes progressively

```python
import asyncio
from orionis.http import response

async def export_rows():
    yield b"id,name\n"
    yield b"1,Ada\n"

async def example():
    result = response.stream(export_rows(), media_type="text/csv")
    assert b"".join([chunk async for chunk in result.getStream()]) == b"id,name\n1,Ada\n"

asyncio.run(example())
```

`stream()` accepts synchronous and asynchronous byte iterables. A generator yielding `str` is invalid for this API. Encode chunks using your selected encoding. Synchronous generators may need delegated execution during delivery: keep the location of blocking work explicit.

## Publishing progress with SSE

```python
from orionis.http import ServerSentEvent, response

async def progress_events():
    for step in range(3):
        yield ServerSentEvent(event="progress", id=str(step), data=str(step))

async def progress():
    return response.eventStream(progress_events())

frame = ServerSentEvent(event="progress", id="7", retry=1500, data="ready").encode()
assert b"event: progress\n" in frame
assert frame.endswith(b"\n\n")
```

`eventStream()` accepts strings and `ServerSentEvent` values. It configures `text/event-stream` and headers to discourage incompatible buffering; manual framing is unnecessary. Multiline `data` produces one `data:` line per line. `event` and `id` reject newlines; `retry` requires a nonnegative integer. `comment` supports comments and keepalives.

An `id` identifies an event; this module neither stores events nor automatically reconstructs history on reconnect. For resumption, maintain a sequence in a durable service and validate incoming cursors. `retry` does not retry the producer on the server.

## Cancellation and closing

Consumption is lazy and follows delivery pace. Use `try/finally` in producers that open cursors, files or subscriptions. Adapter tests cover disconnects, cancellation and iterator closure. Do not suppress `CancelledError` while leaving a producer running. Cleanup through `aclose()`, when provided, must finish before releasing the scope.

`HTTP_MONITOR_DISCONNECTS` controls additional monitoring for ordinary HTTP requests; SSE/WebSocket and endpoint policies may use their own mechanisms. Verify your adapter and deployment settings. A proxy can still buffer output even when the application yields chunks; test the entire path.

Failures before delivery can become an ordinary response. After headers are sent, signal errors through the stream's protocol or end the connection; do not promise to switch to a JSON 500. Background work must not depend on retaining request objects after cleanup.

Evidence: [SSE](../../sse.py), [responses](../../responses.py), [streams](../../adapters/response/streams.py). Tests: [SSE](../../../../tests/http/test_sse.py), [SSE lifecycle](../../../../tests/http/adapters/test_sse_lifecycle.py), [SSE kernel](../../../../tests/http/test_sse_kernel.py). For bidirectional traffic, see [WebSocket](websockets.md).
