# Server-Sent Events (SSE)

SSE sends a sequence of UTF-8 text events over one HTTP response. Orionis exposes
`ServerSentEvent` and `EventStreamResponse` through `orionis.http`, with
`response.eventStream(...)` as the factory entry point. The API is the same under
ASGI and Granian RSGI and uses the existing HTTP routing, middleware and request
scope.

```python
from collections.abc import AsyncIterator
from orionis.http import EventStreamResponse, ServerSentEvent, response


async def notifications() -> AsyncIterator[ServerSentEvent]:
    """Yield the connection marker and an application message.

    Yields
    ------
    ServerSentEvent
        Named events with application-owned cursors.
    """
    yield ServerSentEvent(
        event="connected",
        data="ready",
        id="1",
    )

    yield ServerSentEvent(
        event="message",
        data="Hello",
        id="2",
    )


async def handler() -> EventStreamResponse:
    """Return an event response without consuming its producer.

    Returns
    -------
    EventStreamResponse
        Lazy response consumed by the HTTP adapter.
    """
    return response.eventStream(notifications())
```

Register `handler` with the usual `Route.get(...)` API. A handler may also return
`EventStreamResponse(notifications())` directly. Constructing either response is
synchronous; the HTTP adapter consumes the source when delivering the response.

## Public API and framing

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ServerSentEvent:
    data: str | None = None
    event: str | None = None
    id: str | None = None
    retry: int | None = None
    comment: str | None = None

    def encode(self) -> bytes: ...
```

All fields are optional keyword arguments. Events are immutable. `encode()`
returns UTF-8 bytes, emitting fields in this order: comment, event, id, retry,
data. Every frame ends in `\n\n`, including an event with no fields. Missing
(`None`) fields are omitted; empty strings are preserved as empty field values.
An entirely empty event is a blank frame and does not dispatch a message to an
SSE client.

Client-side interpretation follows the
[SSE event-stream standard](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation).

| Field | Meaning and validation |
|---|---|
| `data` | Text payload. Each line becomes a separate `data: ` line. |
| `event` | Event name. CR and LF are rejected. |
| `id` | Application event identifier. CR, LF and NUL are rejected. An empty value resets the client's event ID. |
| `retry` | Nonnegative integer reconnect delay in milliseconds for the client. Booleans are rejected. |
| `comment` | Comment text. Each line becomes a separate `: ` line; comments do not dispatch message events. |

Text fields accept only `str` or `None`; invalid field types raise `TypeError` at
construction. Invalid `event`/`id` characters and negative `retry` raise
`ValueError`. Data and comments normalize CRLF and CR to LF before splitting
lines; trailing empty lines are retained.

```python
ServerSentEvent(data="first\r\nsecond\rthird").encode()
# b"data: first\ndata: second\ndata: third\n\n"

ServerSentEvent(event="message", id="42", data="hello").encode()
# b"event: message\nid: 42\ndata: hello\n\n"

ServerSentEvent(data="").encode()
# b"data: \n\n"
```

There is no implicit JSON serialization. Serialize structured data explicitly:

```python
import json

event = ServerSentEvent(data=json.dumps({"status": "ready"}))
```

`EventStreamResponse` inherits `StreamingResponse` and accepts the following
arguments; `response.eventStream` accepts the same arguments and returns an
`EventStreamResponse`:

```python
def __init__(
    self,
    content: AsyncIterable[ServerSentEvent | str] | Iterable[ServerSentEvent | str],
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None: ...
```

An item of type `str` has the same framing as `ServerSentEvent(data=item)` but is
encoded directly, without allocating a temporary event. An unsupported item,
including raw bytes, raises `TypeError` when the stream reaches it. A source
which is neither an async iterable nor a synchronous iterable raises `TypeError`
when constructing the response. Pass `["hello"]` for one text event: a bare
string is itself an iterable and produces one event per character. Events are
encoded one at a time into the `AsyncIterable[bytes]` consumed by the existing
response adapters. `getBody()` is
`None`. Use async producers for I/O; synchronous sources execute on the event
loop and must not block it.

## Headers and proxies

The default headers are:

```http
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
X-Accel-Buffering: no
```

Explicit values for these headers are preserved, with case-insensitive header
names. Keep a valid SSE content type for SSE clients. `Content-Length` is removed
even if supplied, and the adapters omit it from SSE output if added later.
Orionis does not add `Connection: keep-alive`; connection management belongs to
the HTTP server, including HTTP/2.

`X-Accel-Buffering: no` is a hint for compatible proxies. Configure the actual
reverse proxy, load balancer and compression middleware to forward incremental
output and allow the desired connection duration. A proxy may buffer or close
an idle connection despite the response headers. Test through the complete
deployment path; a successful transport send does not prove that the final
client has received an event.

## Disconnect, cancellation and ownership

The response owns the acquired source iterator for the delivery lifetime. On
normal completion, disconnect, producer/transport failure or request
cancellation, cleanup closes that iterator with awaited `aclose()` when
available, or `close()` for a synchronous iterator. An unstarted response closes
the source itself if it exposes a close method, without starting iteration.
This also covers header serialization and encoding failures before the transport
starts sending, for both GET and HEAD.
Put application resource cleanup in the producer's `finally` block. Once
started, the iterator is closed without requiring another event to be yielded.

ASGI watches `receive()` for `http.disconnect` concurrently with delivery. A
disconnect cancels the running stream operation, including a producer waiting
for its next event. The watcher consumes and discards remaining `http.request`
messages while waiting. Read any required request body in the handler before
returning the response; do not consume `request.body()` or `request.stream()`
inside the producer concurrently with the watcher.

RSGI sends through `protocol.response_stream(...)` and awaited
`transport.send_bytes(...)`. It watches the supported
`protocol.client_disconnect()` awaitable concurrently, so a silent producer can
also be cancelled on disconnect. Granian's HTTP stream transport has no public
`close()` method; Orionis closes the source iterator and returns control to the
protocol. The disconnect watcher is cancelled and awaited when delivery ends,
because an HTTP keep-alive connection can outlive a response. This contract is
documented in the [Granian 2.8.4 RSGI specification](https://github.com/emmett-framework/granian/blob/v2.8.4/docs/spec/RSGI.md#http-protocol-interface).

Both adapters stop and await their temporary tasks before returning. A normal
client disconnect is an incomplete delivery. Producer, transport and cleanup
errors propagate; request cancellation remains `CancelledError` when cleanup
succeeds. A cleanup failure takes precedence and retains cancellation as its
cause. Simultaneous delivery and watcher errors are preserved in an exception
group. Completion order is recorded by callbacks: when both operations finish
in the same event-loop turn, an earlier disconnect still suppresses background
work, while an earlier successful delivery remains successful. Producers must
cooperate with cancellation: blocking synchronous work or suppressing
`CancelledError` prevents timely shutdown.

The framework protects and awaits its explicit asynchronous iterator close.
If cancellation can arrive while the producer is already awaiting its own
resource release, protect and await that critical operation as well. Cancelling
a producer cannot restart cleanup code abandoned inside its `finally` block.

`HEAD` sends headers and an empty final body without starting or consuming the
SSE producer. Ordinary `StreamingResponse` instances do not gain SSE disconnect
watching merely by setting `Content-Type: text/event-stream`.

## Request scope and background tasks

`KernelHTTP` awaits response delivery inside the existing request application
scope. Scoped dependencies stay available throughout streaming and cleanup;
SSE does not open an additional scope. Request resources are released when
delivery and any successful background work finish, including failure and
cancellation paths.

A response background task runs only after normal stream exhaustion and
successful delivery and cleanup. An early disconnect, producer failure,
transport failure, cleanup failure or cancellation skips background work. Use
the producer's `finally` for required resource release: a background task is
not a disconnect or cleanup callback. `HEAD` follows the existing successful
response background behavior without consuming the source.

## Manual heartbeat and reconnection

Emit a comment when your application wants a heartbeat:

```python
yield ServerSentEvent(comment="ping")
# b": ping\n\n"
```

Orionis creates no heartbeat timer, scheduler or periodic task. The application
chooses when to emit comments. Comments can keep activity visible to proxies
without delivering a message event, but deployment idle timeouts still apply.

Read a reconnect cursor through the ordinary request header API:

```python
from orionis.http import Request


def last_event_id(request: Request) -> str | None:
    """Read the reconnect cursor without interpreting its application meaning.

    Parameters
    ----------
    request : Request
        Current HTTP request.

    Returns
    -------
    str | None
        Client-provided cursor, or None when the header is absent.
    """
    return request.headers.get("Last-Event-ID")
```

`id` sets the event cursor offered to the client; a reconnecting client may send
it back in `Last-Event-ID`. Validate and interpret that header in application
code. `retry` advises the client about reconnect timing. Orionis does not
reconnect on the server, store sessions or event history, persist cursors or
replay missed events. A new HTTP request gets its own ordinary request scope.

## Performance and concurrency

Delivery follows `produce one event → encode UTF-8 → await transport send →
request the next event`. The transport's awaited send provides backpressure.
Orionis adds no event queue, complete-stream copy, worker thread, polling,
internal sleeps or global connection state. Memory scales with the current
event and the producer's own state, not with the number of events already sent;
transport/proxy buffering is outside this guarantee.

Each open SSE request retains its request scope and counts toward the existing
HTTP request concurrency limit until it finishes. Plan capacity for long-lived
requests and keep per-request dependencies small. Use cancellation-aware async
I/O and release subscriptions/resources in `finally`. Broadcasting, pub/sub,
event storage and authentication policies remain application concerns.

## Initialization and dependency injection

| Component | Eager work | Deferred work |
|---|---|---|
| HTTP package initializer | Declare the public export table. | Resolve and cache exports on first access. |
| `ServerSentEvent` | Validate immutable field types, metadata and retry once. | Encode bytes only when `encode()` is called; do not cache arbitrary payloads. |
| `EventStreamResponse` | Validate response metadata, retain the source and set headers. | Do not call the source iterator, perform I/O or create tasks in `__init__`. |
| `_EventStreamIterator` | Classify the source protocol and initialize empty state. | Acquire the source iterator on the first pull; create cleanup work only on close. |
| Response factory and adapters | Construct stateless objects during import or boot. | No lazy service lookup is needed for these objects. |
| HTTP controller | Preload its class and dependency plans during kernel boot. | Construct the controller and resolve request/scoped services inside each request. |

Keep blocking I/O out of constructors and synchronous producers. Controllers
continue to use `Container.build()` and `Container.call()`, and function handlers
use `Container.invoke()`. SSE does not introduce a provider, an independent
container, per-event reflection, or a new construction path for models, mailers
or jobs. Request-scoped objects must not be cached globally. See the
[container](../../container/docs/README.md) and
[introspection](../../introspection/docs/README.md) manuals for those contracts.

## Review findings

The review covered all 12 pending Python files and the four HTTP/SSE manuals.
No critical defect was confirmed within this scope; that is not a claim that
every possible application producer or deployment is safe.

### High: resource ownership before sending

Header serialization could fail before either adapter entered its stream
cleanup block. The owned source then received no explicit close. Both adapters
now await closure on this error path, including HEAD and ASGI encoding failures.
This prevents abandoned subscriptions or handles; extra CPU and cleanup latency
occur only on failed preparation. Cleanup can still wait indefinitely if an
application finalizer does not cooperate. Five previously failing scenarios are
covered by two regression methods.

### High: disconnect and completion ordering

The former `asyncio.wait(FIRST_COMPLETED)` result could contain both tasks and
did not preserve which finished first. This could run background work after an
earlier disconnect. A shared callback records the first completion in a future;
both tasks are still joined and simultaneous errors remain visible. Coordination
uses constant space and no longer constructs the `wait()` result sets. The
trade-off is explicit callback registration and removal, covered by tests for
both completion orders.

### Medium: event encoding and temporary objects

Raw text previously constructed a frozen dataclass and validated unused fields
for every message. Direct text framing removes that object and validation work.
Structured data and comments now prefix their lines with `str.replace`, without
`split()` lists, generator expressions or one temporary string per line. Time
remains linear in payload bytes, but the frame assembly list has at most five
elements instead of growing with the line count. Output bytes and necessary
normalization copies remain proportional to payload size. The two framing paths
require equivalence tests; neither caches payloads or changes the public API.

### Low: cleanup and response setup

One asynchronous close no longer needs a one-element `gather()` result list.
Shared cleanup waiting protects a successful completion notification and then
reads the owned task's result. This also avoids Python 3.14's shielded-future
error logging for a failure that the owner already handles. Repeated cancellation
still waits for cleanup and re-raises cancellation. The trade-off is a small
set of private lifecycle helpers; there is no per-event cleanup cost.

Header serializers skip the additional filtering list when `Content-Length` is
absent, saving one list and one header scan per serialization. The normal
serialization still scales with the number of headers; a later explicit length
continues through the filtering path. Returned lists and response metadata keep
their existing mutability. Redundant SSE iterator acquisition was removed.

Validation and RSGI dispatch were split into focused helpers to satisfy lint
complexity limits. No rule exclusions or new suppression comments were added.
Implementation methods use camelCase, module functions use snake_case, and
Python dunders and required foreign-protocol aliases retain their standard names.

## Measured results and verification

Measurements used CPython 3.14.6 on Windows 11. The minimum remains Python 3.14.
Encoding results are medians of seven alternating rounds of 100,000 operations.
The baseline retained the previous split/join encoder; text measurements include
its temporary `ServerSentEvent` construction, while structured-event measurements
use a prebuilt event with `event="update"`, `id="42"` and `comment="ping"`.
Byte equality was checked before timing. Payloads were `"ready"`,
`"line\r\n" * 64`, and `"\u00e9\u4e16\u754c" * 32`.

| Encoding case | Before (us) | After (us) | Ratio | Peak before/after (bytes) |
|---|---:|---:|---:|---:|
| Short text | 1.319 | 0.165 | 7.97x | 1276 / 242 |
| Short structured event | 1.005 | 0.489 | 2.06x | 1024 / 586 |
| Text with 64 CRLF separators | 11.052 | 2.761 | 4.00x | 8808 / 2001 |
| Structured event with 64 CRLF separators | 11.044 | 3.709 | 2.98x | 8460 / 3044 |
| Unicode text | 2.474 | 0.651 | 3.80x | 1585 / 699 |
| Unicode structured event | 2.128 | 1.272 | 1.67x | 1417 / 1281 |

Memory values are transient `tracemalloc` peaks over 1,000 operations, not retained
memory, RSS, or bytes per connection. Header methods were measured separately
with identical header data, method dispatch and inheritance: nine alternating
rounds of 200,000 calls. ASGI headers measured 0.833 to 0.699 us (1.19x); RSGI
headers measured 0.572 to 0.445 us (1.29x). A function-versus-method comparison
was discarded because it did not measure equivalent call paths.

Verified checks:

- HTTP: 869/869; container: 253/253; introspection: 1022/1022.
- SSE includes 66 tests, seven added during this review, with 32 simultaneous
    controller requests per transport and mixed completion/disconnect outcomes.
- AST audit: 84 runtime and 139 test definitions with valid naming, docstrings,
    annotations and no duplicate method definitions.
- `python -m ruff check .` passed; SonarQube for IDE analysis and editor
    diagnostics were clean for the 12 pending Python files under existing settings.

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor test --start-dir=tests/http --verbosity=0
.\.venv\Scripts\python.exe reactor test --start-dir=tests/container --verbosity=0
.\.venv\Scripts\python.exe reactor test --start-dir=tests/introspection --verbosity=0
.\.venv\Scripts\python.exe -m ruff check .
```

These are local correctness checks and microbenchmarks, not HTTP throughput or
latency measurements against Starlette. Native network backpressure, deployment
proxies, multi-process saturation and a remote SonarQube Quality Gate were not
certified by this review.
