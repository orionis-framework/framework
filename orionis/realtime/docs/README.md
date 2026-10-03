# Realtime Hubs

Orionis Realtime adds explicit, typed, bidirectional RPC to the ordinary
[WebSocket API](../../http/docs/websockets.md). Raw sockets stay independent of
Hubs; the optional Hub runtime uses the same socket, Application, route compiler,
middleware and dependency container under ASGI and RSGI.

The complete wire specification is [Orionis Realtime Protocol v1](protocol-v1.md).
There is no SignalR compatibility and no JavaScript SDK in this release.

## A first Hub

```python
from orionis.realtime import Hub, remote
from orionis.support.facades import Route

class CalculatorHub(Hub):
    @remote
    async def add(self, a: int, b: int) -> int:
        return a + b

Route.hub("/hubs/calculator", CalculatorHub)
```

After the connection receives `ready`, it sends
`{"type":"invoke","id":"1","target":"add","args":[2,3]}` and receives
`{"type":"completion","id":"1","result":5}`. A method returning `None`
produces an explicit JSON `null` result. RPC errors complete that invocation;
ordinary argument or method errors do not close the connection.

Only `@remote` methods are callable from a client. A public Python helper is not
exposed automatically. `@remote(name="sendMessage")` defines a public alias
without wrapping the method. Invalid/private names, duplicate aliases,
class/static methods, variadics, positional-only arguments and unresolved
annotations fail during registration. All client and injected parameters need
explicit annotations. Import the types used in those annotations at runtime so
the framework can resolve them during boot.

Both async methods and short synchronous methods work. Synchronous code executes
on the application's event loop; no thread is created. Use asynchronous services
for I/O, and queues for durable or long-running work.

## Dependency injection and invocation scopes

```python
from app.services.orders import OrderService
from orionis.realtime import Hub, remote

class OrdersHub(Hub):
    def __init__(self, service: OrderService) -> None:
        self.service = service

    @remote
    async def find(self, order_id: int, service: OrderService) -> object:
        return await service.find(order_id)
```

The client supplies `order_id` only. `service` always comes from the container;
attempting to send a named service parameter is rejected. Positional argument
indexes skip injected services. Registered services, unregistered concrete
service classes, framework context and nullable service annotations remain
container-owned. A declaration such as `service: OrderService | None = None`
still resolves `OrderService`; it does not give the client ownership.

Primitive types, supported typed collections, enums and `msgspec.Struct` schema
parameters are client-bound. Conversion uses strict msgspec validation, and
Orionis schemas run the existing schema rules. Converted schema arguments and
declared defaults are passed explicitly, so RPC never reads an HTTP request body.
Ambiguous service/data unions are rejected at boot.

The kernel owns one scope for the connection. Each admitted invocation opens a
fresh, independent `contextvars` scope and builds a new Hub through DI. Scoped
services differ between concurrent invocations; constructor and method injection
within one invocation share that invocation's services. Framework connection
objects are explicitly republished in the invocation scope:

```text
connection scope
    ├── invocation A → Hub A → scoped services A
    └── invocation B → Hub B → scoped services B
```

Hub instances are not a place to store connection or global mutable state.
`HubContext` is frozen and contains `connection_id`, `socket` and `user`.
`connection_id` identifies a connection, not a user or login session.

## Lifecycle and authentication

```python
class ChatHub(Hub):
    async def onConnect(self) -> None:
        if self.context.user is None:
            await self.context.socket.reject(status_code=401)
            return
        await self.groups.join("authenticated")

    async def onDisconnect(self, code: int, reason: str | None = None) -> None:
        pass
```

The connection is provisionally owned while `onConnect` runs, allowing group
membership changes. It is eligible for targeting only after the ready message
has been sent. The runtime accepts the socket after a successful hook unless
the hook already accepted it. Do not invoke clients or send protocol messages
from `onConnect`; clients have not received `ready` yet.

After any exit, owned invocation tasks and pending client futures are released,
groups and the registry entry are removed, then `onDisconnect` runs. Hook errors
are logged without payloads and do not prevent socket cleanup. Hook completion
is bounded during disconnect, and the existing kernel shutdown hook cancels
connection owners. Application tasks must cooperate with cancellation.

Use WebSocket-specific middleware with
`Route.hub(...).middleware(YourWebSocketMiddleware)`. Its contract is
`handle(socket: WebSocket, call_next: WebSocketNext) -> None`; HTTP middleware
requiring Request/Response cannot be attached. Handshake headers, cookies,
query, path, client/server and scheme are available on the socket.

HTTP session middleware and automatic session/token identity restoration are
not run for WebSocket routes. Application connection middleware should validate
its handshake credential using its existing identity/guard services and bind
the existing Auth context, for example after obtaining `validated_user` and
an injected `IPermissionRepository` named `permissions`:

```python
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context

bind_auth_context(AuthenticationContext(
    identity=validated_user,
    guard="websocket",
    repository=permissions,
))
```

No separate realtime ACL is created. Remote methods can use `await Auth.can(...)`
or injected authorization services as usual. Authentication of a connection
does not authorize every operation or group join. The built-in context is copied
into each invocation with its identity and credential restrictions preserved;
authorization snapshots and locks are independently resolved per invocation.
Custom `IAuthenticationContext` implementations do not have an implicit cloning
contract in this release and must arrange application-owned adaptation to the
built-in context for Hub invocations. A long-lived connection does not
automatically revalidate its original credential on every call; applications
requiring revocation checks must perform those checks as part of authorization.

## Groups, broadcasts and targeting

```python
class ChatHub(Hub):
    @remote
    async def joinRoom(self, room: str) -> None:
        # Authorize access to room in application code before joining.
        await self.groups.join(room)

    @remote
    async def sendMessage(self, room: str, message: str) -> dict:
        result = await self.clients.group(room).send(
            "messageReceived", {"room": room, "message": message},
        )
        return {"sent": result.sent, "failed": result.failed}
```

`await self.groups.leave(name)` removes membership idempotently. Joining the
same group again does not consume another group slot. Disconnect removes all
memberships and empty groups. Groups belong to a Hub namespace: the same group
name in different Hub classes does not share recipients.

| Selection | Recipients |
|---|---|
| `self.clients.all` | All ready connections to this Hub. |
| `self.clients.caller` | This connection only. |
| `self.clients.others` | All other ready connections to this Hub. |
| `self.clients.client(id)` | One explicit connection in this Hub. |
| `self.clients.clients(ids)` | Explicit identifiers with duplicates removed. |
| `self.clients.group(name)` | Ready members of a Hub-local group. |

Each selection supports `await target.send(event, *args) -> BroadcastResult`.
`sent` counts successful transport deliveries and `failed` counts recipients
that disappeared or whose write failed. This does not acknowledge execution of
the client's event handler. A recipient's failure does not stop other recipients.
An explicit unavailable client is a failed delivery; an empty group returns zero
counts. Caller/others selectors require a Hub connection context.

The broadcast implementation encodes once per participating codec and uses at
most `broadcast_concurrency` workers. It shares immutable strings/bytes across
connections and awaits each socket's backpressure; there is no unlimited output
queue and no task per recipient in a large broadcast.

## Invoking a client and sending from services

```python
state = await self.clients.client(connection_id).invoke(
    "getState", {"section": "orders"}, timeout=5,
)
```

`invoke` awaits a correlated client completion, while `send` only awaits network
delivery. Invoke is available only for one explicit client or `caller`. A
multi-recipient target raises `RuntimeError` for invoke. The server owns a
bounded future map per connection and removes entries on completion, timeout,
cancellation and disconnect. Duplicate/unknown completions are ignored.
Timeout raises `TimeoutError`, a disconnected target raises `ConnectionError`,
and a client-reported error raises
`orionis.realtime.errors.ClientInvocationError` with a sanitized message.

The normal eager provider and facade make the same targets available outside a
Hub, including controllers and application services:

```python
from orionis.support.facades import Realtime

await Realtime.hub(ChatHub).group("general").send(
    "messageReceived", {"message": "Scheduled maintenance soon"},
)

state = await Realtime.hub(DeviceHub).client(connection_id).invoke(
    "getState", timeout=5,
)
```

The facade delegates to the container-managed `IConnectionManager`; it owns no
parallel registry. Application services can inject that contract instead of
using the facade. The shipped `ConnectionManager` stores only the current
worker's connections. Replacing the contract is the extension point for future
distributed delivery; no Redis/Kafka/other backplane ships here.

**Multi-worker limitation:** sends and broadcasts reach only connections in the
same worker as the calling service. There is no offline queue or reconnect replay.
WebSocket send/RPC is realtime, non-durable. Queue jobs provide durable execution.

## Streaming and cancellation

```python
from collections.abc import AsyncIterator
from app.services.progress import ProgressService

class ProgressHub(Hub):
    @remote
    async def watchProgress(
        self, process_id: str, service: ProgressService,
    ) -> AsyncIterator[int]:
        async for value in service.watch(process_id):
            yield value
```

The runtime sends `stream_item` for each yielded item and `stream_complete` at
the end. It awaits the send before advancing the producer, preserving network
backpressure. A producer or serialization error produces a controlled terminal
error. The iterator's `aclose()` is awaited when present, including cancellation.
Producer cleanup and invocation scope release finish before the terminal
success/error envelope is sent.

The client cancels by sending `{"type":"cancel","id":"its-invocation-id"}`.
Only that invocation is cancelled; its `finally` runs and its scope closes.
Repeated/unknown cancellation is harmless. An in-flight socket write may finish
before the terminal cancellation error; it is not torn down by cancelling a
single invocation. Disconnect cancels all owned work. Do not swallow
`asyncio.CancelledError` in application methods.

Once execution and cleanup commit an outcome, a cancellation racing its final
delivery cannot replace that outcome or generate a second terminal response.
The client may reuse the ID after receiving its terminal envelope. The server
still owns the final delivery task until it finishes, including cleanup on
disconnect or shutdown.

Async generators and methods annotated as async iterables/iterators have no
default stream lifetime deadline. Optional wire `timeout` is finite, positive
and cannot exceed `invocation_timeout`. Ordinary calls use that configured
deadline. These deadlines do not limit the connection itself.

An invocation deadline covers DI, binding, execution, stream item delivery and
producer cleanup. Final `completion`/`stream_complete` delivery follows scope
release and runs outside that deadline while still awaiting network backpressure.
It can therefore finish after the configured duration without generating a
second timeout outcome. Active invocations and invocations finishing their
terminal delivery both count toward `max_concurrent_invocations`; slow clients
cannot create unlimited terminal delivery tasks. A client needing a deadline
for receipt of the terminal envelope should also use a local timer.

## Configuration, errors and implementation

Define `config/realtime.py` using the normal frozen entity convention:

```python
from dataclasses import dataclass
from orionis.foundation.config.realtime import RealtimeConfig

@dataclass(frozen=True, kw_only=True)
class BootstrapAppRealtime(RealtimeConfig):
    max_concurrent_invocations: int = 16
    max_pending_client_invocations: int = 32
    invocation_timeout: float = 30.0
    client_result_timeout: float = 30.0
    broadcast_concurrency: int = 32
    max_groups_per_connection: int = 64
    max_message_size: int = 1024 * 1024
```

All counts are positive integers and timeouts are finite positive numbers.
Raw `http.websocket` admission and message-size limits apply as well; see the
[WebSocket documentation](../../http/docs/websockets.md). Codec choice belongs
to `Route.hub(..., protocol="json" | "msgpack")`, not to a global negotiation
service. MessagePack needs no extra Python dependency because msgspec is already
part of Orionis.

Invocation errors use stable codes such as `invalid_arguments`,
`validation_error`, `method_not_found`, `busy`, `timeout`, `cancelled`,
`unauthorized`, `forbidden` and `internal_error`. Error text is generic and
does not contain exception representations, tracebacks, paths or credentials.
Malformed wire messages and fatal lifecycle failures close the connection.
Messages are not logged by default; relevant protocol and lifecycle failures
are logged without RPC payloads.

| Component | Responsibility |
|---|---|
| `Hub`, `HubContext`, `remote` | Application API and explicit exposure. |
| `metadata.compile_hub` / `RemoteMethod` | Cached immutable dispatch and strict data/DI binding. |
| `HubProtocol` | Typed msgspec decoding and JSON/MessagePack envelope encoding. |
| `HubRuntime` | Lifecycle, invocation scopes, streaming and cancellation. |
| `RealtimeConnection` | One connection's active tasks, pending results and serialized writes. |
| `IConnectionManager` / `ConnectionManager` | Worker-local registry, Hub namespaces and groups. |
| `HubClients`, `HubGroups`, `BroadcastResult` | Small targeting and membership API. |
| `RealtimeProvider` / `Realtime` | Container registration and the normal facade. |

Dispatch metadata is compiled during route registration and cached with a
bounded LRU; it contains no Hub instances. The per-message path performs codec
decode, dictionary dispatch, binding/conversion, container invocation, encode
and awaited send. There is no per-message class scan, network-controlled import,
thread pool, mandatory heartbeat task, durable buffer or BackgroundTask.
ASGI and RSGI differences stay in raw transport adapters, including RSGI's
unavailable custom accept headers/subprotocol and close-frame details. No
benchmark claims are made without running the benchmark harness.
