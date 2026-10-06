# orionis.realtime

> `orionis.realtime` adds typed, bidirectional, invocation-scoped RPC and event delivery to Orionis WebSocket routes.

## Overview

Realtime routes bind a `Hub` class to a native WebSocket endpoint using JSON text frames or MessagePack binary frames. Only ordinary instance methods explicitly marked with `@remote` are callable. Orionis compiles their argument, schema, dependency-injection, and streaming plans at registration, then creates a fresh hub instance for each invocation.

Each connection owns bounded server invocations, pending client results, group memberships, and ordered writes. The default `ConnectionManager` is worker-local; it provides hub-isolated client selection and bounded broadcast fan-out without pretending to be a distributed backplane.

## Requirements

- Python 3.14 or newer.
- A booted Orionis HTTP application with WebSocket-capable ASGI or RSGI serving.
- A `Route.hub(...)` registration using `json` or `msgpack`.
- JSON/MessagePack-serializable arguments and results; Orionis `Schema` values are additionally validated.

## Quick start

```python
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub


class MathHub(Hub):
    @remote
    async def add(self, first: int, second: int) -> int:
        return first + second


methods = compile_hub(MathHub)
assert tuple(methods) == ("add",)
assert methods["add"].bind([2, 3], {}) == {"first": 2, "second": 3}
```

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Explicit remote surface

`@remote` attaches metadata without wrapping the function. A remote name must be a public Python identifier of at most 128 characters; an optional alias controls the wire target. Class/static methods, private targets, duplicate aliases, positional-only arguments, variadics, missing annotations, and ambiguous service/data annotations are rejected at compilation.

### Argument binding and DI

Client-owned parameters are typed data annotations supported by `msgspec`; container dependency annotations are resolved separately and cannot be supplied by the client. Defaults and keyword-only parameters are supported. Nested Orionis schemas run their framework validation rules after conversion.

### Invocation lifecycle

The client sends `invoke`, may send `cancel`, and receives `completion` or a sequence of `stream_item` followed by `stream_complete`. Scalar invocations use the configured default timeout unless overridden. Streams have no default lifetime limit, but an explicit envelope timeout applies. Cleanup cancels and joins connection-owned work.

### Bidirectional calls

Hub methods can send events to clients and can invoke one selected client while awaiting a correlated `completion`. Pending results are bounded and time-limited. Client-provided error text is converted to a sanitized `ClientInvocationError` rather than copied into server diagnostics.

### Groups and process boundaries

Groups are namespaced by Hub class. Membership is automatically removed on disconnect. The built-in registry only knows connections in the current worker/process; replace `IConnectionManager` or add an external backplane for cross-worker broadcast.

## Module structure

| Path | Responsibility |
|---|---|
| `hub.py`, `decorators.py`, `metadata.py` | Hub lifecycle, explicit remote markers, compiled dispatch plans. |
| `runtime.py`, `connection.py` | WebSocket loop, invocation tasks, result correlation, cleanup, ordered writes. |
| `protocol.py` | Strict Realtime v1 JSON/MessagePack envelopes and limits. |
| `clients.py`, `groups.py` | Recipient selection, events, client RPC, and membership. |
| `manager.py` | Worker-local connection/group registry and bounded broadcasts. |
| `entities.py`, `errors.py` | Broadcast result and safe application/protocol errors. |
| `provider.py`, `config.py` | DI bindings, facade pinning, and validated configuration export. |
| `contracts/` | Replaceable connection-manager and connection boundaries. |

## Public API

The root lazily exports `Hub`, `HubContext`, `remote`, `HubProtocol`, `HubClients`, `HubGroups`, `ConnectionManager`, and `BroadcastResult`.

### `Hub`

`onConnect()` runs after registration but before the ready envelope. It may join groups or reject setup. `onDisconnect(code, reason)` runs after owned invocations and registrations are released. Per invocation, Orionis sets `context`, `clients`, and `groups` on a new Hub instance.

### Client selection

`HubClients` exposes `.all`, `.caller`, `.others`, `.client(id)`, `.clients(ids)`, and `.group(name)`. Every target supports `send(target, *args)`. Only a single `.client(...)` or `.caller` target supports `invoke(...)` because it needs one correlated result.

### Application service access

`Realtime.hub(MyHub)` returns `HubClients` without a caller, suitable for broadcasting from controllers, jobs, listeners, or other services. Caller-specific selectors remain unavailable outside an active hub invocation.

### Safe failures

Raise `RPCError(code, message)` for a deliberate client-visible application failure. Authentication/authorization, validation, cancellation, timeout, unknown target, and internal failures use stable sanitized codes; unexpected exception details are not sent to the peer.

## Common workflows

### Register a route

Use `Route.hub("/realtime", MyHub)` for JSON or pass `protocol="msgpack"`. The selected codec determines frame type for the whole connection; JSON rejects binary input and MessagePack rejects text input.

### Broadcast an event

Inside a hub, choose `clients.all`, `caller`, `others`, a client set, or a group, then await `.send(...)`. The result reports successful and failed recipient counts; offline messages are not persisted.

### Stream results

Return an `AsyncIterator`/`AsyncIterable` or implement an async generator remote method. Each yielded item is sent under backpressure. Cancellation and disconnect close the iterator and release the invocation id.

### Invoke a client

Await `clients.caller.invoke(...)` or `clients.client(id).invoke(...)`. The connection reader stays active so it can correlate the peer's completion. Always use a bounded timeout appropriate to the operation.

## Examples

### Alias a remote method and compile a stream

```python
from collections.abc import AsyncIterator
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub


class FeedHub(Hub):
    @remote(name="updates")
    async def stream_updates(self, count: int) -> AsyncIterator[int]:
        for value in range(count):
            yield value


method = compile_hub(FeedHub)["updates"]
assert method.method_name == "stream_updates"
assert method.is_stream is True
assert method.bind([], {"count": 2}) == {"count": 2}
```

Validation: **Executed successfully** on CPython 3.14.6.

### Encode Realtime v1 envelopes

```python
import msgspec
from orionis.realtime import HubProtocol

json_protocol = HubProtocol("json", max_message_size=4096)
msgpack_protocol = HubProtocol("msgpack", max_message_size=4096)
envelope = {"type": "send", "target": "refresh", "args": [1]}

text = json_protocol.encode(envelope)
binary = msgpack_protocol.encode(envelope)
assert isinstance(text, str)
assert isinstance(binary, bytes)
assert msgspec.json.decode(text)["target"] == "refresh"
```

Validation: **Executed successfully** on CPython 3.14.6.

### Build validated limits

```python
from orionis.realtime.config import RealtimeConfig

config = RealtimeConfig(
    max_message_size=64 * 1024,
    max_concurrent_invocations=8,
    max_pending_client_invocations=16,
    invocation_timeout=10.0,
    client_result_timeout=5.0,
    broadcast_concurrency=12,
    max_groups_per_connection=20,
)
assert config.max_message_size == 65_536
assert config.broadcast_concurrency == 12
```

Validation: **Executed successfully** on CPython 3.14.6.

### Broadcast safely to an empty local registry

```python
import asyncio
from orionis.realtime import ConnectionManager
from orionis.realtime.config import RealtimeConfig


async def example() -> None:
    manager = ConnectionManager(RealtimeConfig())
    result = await manager.hub(MathHub).all.send("refresh", {"version": 1})
    assert result.sent == 0
    assert result.failed == 0


asyncio.run(example())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Register routes and broadcast from application code

```python
from orionis.support.facades import Realtime, Route

Route.hub("/realtime/math", MathHub)
Route.hub("/realtime/feed", FeedHub, protocol="msgpack")


async def notify_refresh() -> None:
    await Realtime.hub(MathHub).all.send("refresh", {"version": 2})
```

Validation: **Import and syntax validated** on CPython 3.14.6; registration and delivery require a booted application.

## Configuration

| Environment variable | Default | Scope |
|---|---:|---|
| `REALTIME_MAX_MESSAGE_SIZE` | 1 MiB | Incoming encoded message bytes. |
| `REALTIME_MAX_CONCURRENT_INVOCATIONS` | 16 | Active client-to-server calls per connection. |
| `REALTIME_MAX_PENDING_CLIENT_INVOCATIONS` | 32 | Awaited server-to-client results per connection. |
| `REALTIME_INVOCATION_TIMEOUT` | 30s | Default scalar server-call timeout. |
| `REALTIME_CLIENT_RESULT_TIMEOUT` | 30s | Default client-result deadline. |
| `REALTIME_BROADCAST_CONCURRENCY` | 32 | Concurrent sends in one local broadcast. |
| `REALTIME_MAX_GROUPS_PER_CONNECTION` | 64 | Memberships owned by one connection. |

All counts and byte budgets are positive integers; timeouts are finite positive seconds. Configuration is loaded once by `RealtimeProvider` as an immutable `RealtimeConfig`.

## Integration with Orionis

`Route.hub` stores Hub type and protocol in the native route. The HTTP kernel upgrades the connection, authenticates within its normal connection scope, and delegates to `HubRuntime`. `RealtimeProvider` binds the config and replaceable `IConnectionManager` and pins the `Realtime` facade.

The container constructs each Hub invocation, resolves declared service parameters, and exposes the current authenticated identity as `HubContext.user`. Middleware and route authentication still protect the WebSocket handshake; `@remote` controls dispatch exposure, not identity policy by itself.

## Errors and edge cases

- Invalid protocol envelopes close with 1002; wrong frame kind uses 1003; oversized messages use 1009.
- Invocation ids are bounded printable ASCII without spaces. Targets/aliases are public identifiers; calls allow at most 64 positional and 64 keyword entries.
- Unknown/duplicate completion ids are ignored and not retained.
- A failed socket write closes the connection and cancels its owner so later writes cannot overtake it.
- `onConnect` failure prevents readiness. Disconnect cleanup is idempotent and removes all groups.
- Broadcast snapshots ids but rechecks availability immediately before each send; disconnects count as failed recipients.
- `BroadcastResult` reports delivery only; it is not an acknowledgement that client code handled the event.

## Performance and concurrency

Remote reflection, type plans, and schema validation plans are cached (up to 1024 Hub classes). Codecs are reused per connection and broadcast payloads are encoded once per codec. A write lock preserves frame order and naturally applies socket backpressure.

Per-connection invocation/pending/group limits and broadcast worker limits bound memory and task fan-out. Invocation tasks are independent, but Hub instances are not shared between them. The default connection manager must be accessed on the application's event loop and does not synchronize across processes.

## Compatibility

The Orionis Realtime envelope version is 1 and is distinct from external SignalR protocols. JSON uses text WebSocket messages; MessagePack uses binary messages. Both native ASGI and RSGI adapters are covered by integration tests. Clients must implement ready, invoke, completion, cancel, ping/pong, send, and stream envelopes they use.

## Verification notes

- `tests/realtime`: **79 test methods passed** with the Orionis runner on CPython 3.14.6.
- Six bilingual documentation programs were compiled; five standalone programs were executed successfully.
- Route/facade integration was import/syntax validated because it requires a booted router and live connections.
- Evidence covered JSON/MessagePack wire behavior, real ASGI/RSGI sockets, metadata compilation, DI, auth, groups, broadcasts, bidirectional results, cancellation, streaming, cleanup, and configuration limits.

