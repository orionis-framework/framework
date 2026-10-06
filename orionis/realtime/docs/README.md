# orionis.realtime

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.realtime initializer exports 8 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.realtime/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| BroadcastResult | from orionis.realtime import BroadcastResult | [entities.py](../entities.py) | BroadcastResult | Count delivered and failed recipients without retaining connections. |
| ConnectionManager | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | ConnectionManager | Own worker-local connections and isolate every group by Hub class. Registry mutations contain no await points and run on the application's event loop. Delivery snapshots identifiers before awaiting network I/O. Replacing IConnectionManager is the extension point for distributed delivery; the default registry never crosses process or worker boundaries. |
| ConnectionManager.config | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def config(self) -> RealtimeConfig | Return the immutable application limits used by Hub lifecycles. Returns ------- RealtimeConfig Application-wide invocation, group and broadcast limits. |
| ConnectionManager.connectionCount | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def connectionCount(self) -> int | Return the number of owned, including provisional, connections. Returns ------- int Number of registered connections regardless of readiness. |
| ConnectionManager.groupCount | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def groupCount(self) -> int | Return the number of nonempty Hub-local groups. Returns ------- int Number of groups with at least one registered member. |
| ConnectionManager.register | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def register(self, connection: RealtimeConnectionLike) -> None | Own one provisional connection before its onConnect hook. Parameters ---------- connection : RealtimeConnectionLike Connection with a cryptographically generated unique identifier. Returns ------- None Register the connection, its Hub namespace and empty memberships. Raises ------ ValueError If its identifier is invalid or already belongs to a connection. |
| ConnectionManager.unregister | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def unregister(self, connection: RealtimeConnectionLike) -> None | Release owned registry entries and every group reference. Parameters ---------- connection : RealtimeConnectionLike Exact connection instance to release; repeated release is harmless. Returns ------- None Remove ownership without touching an instance that reused an ID. |
| ConnectionManager.get | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def get(self, connection_id: str, hub: type[Hub] / None) -> RealtimeConnectionLike / None | Look up a ready recipient without crossing an optional Hub boundary. Parameters ---------- connection_id : str Identifier of the requested connection. hub : type[Hub] / None, optional Required owning Hub class, or None to omit namespace filtering. Returns ------- RealtimeConnectionLike / None Ready, nonclosing connection in the requested namespace, or None. |
| ConnectionManager.snapshot | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def snapshot(self) -> tuple[RealtimeConnectionLike, ...] | Snapshot all owned connections for bounded lifecycle shutdown. Returns ------- tuple[RealtimeConnectionLike, ...] Active and provisional connections owned at the time of the call. |
| ConnectionManager.connectionIds | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def connectionIds(self, hub: type[Hub]) -> tuple[str, ...] | Snapshot ready connection identifiers in one Hub namespace. Parameters ---------- hub : type[Hub] Owning Hub class. Returns ------- tuple[str, ...] Current ready recipients; no connection objects are retained. |
| ConnectionManager.groupIds | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def groupIds(self, hub: type[Hub], group: str) -> tuple[str, ...] | Snapshot ready group members without crossing Hub namespaces. Parameters ---------- hub : type[Hub] Owning Hub class. group : str Group name within that Hub. Returns ------- tuple[str, ...] Current ready recipients of the named group. Raises ------ ValueError If the group name is invalid. |
| ConnectionManager.join | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def join(self, connection_id: str, group: str) -> None | Join an active or provisional connection to a bounded group set. Parameters ---------- connection_id : str Owned connection, including one in its onConnect hook. group : str Hub-local group name, at most 256 characters. Returns ------- None Add membership without consuming another slot for repeated joins. Raises ------ ValueError If the group name is invalid. ConnectionError If this connection is absent or closing. RuntimeError If joining another group would exceed its configured limit. |
| ConnectionManager.leave | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def leave(self, connection_id: str, group: str) -> None | Remove membership idempotently and discard empty group entries. Parameters ---------- connection_id : str Connection whose membership is being released. group : str Hub-local group name. Returns ------- None Remove the membership if still owned. Raises ------ ValueError If the group name is invalid. |
| ConnectionManager.hub | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | def hub(self, hub: type[Hub]) -> HubClients | Return application-service client targets for a Hub namespace. Parameters ---------- hub : type[Hub] Hub class whose clients should receive events or invocations. Returns ------- HubClients Client selectors without a connection-specific caller. Raises ------ TypeError If the supplied class is not a Hub subclass. |
| ConnectionManager.broadcast | from orionis.realtime import ConnectionManager | [manager.py](../manager.py) | async def broadcast(self, hub: type[Hub], connection_ids: tuple[str, ...], envelope: object) -> BroadcastResult | Encode once per codec and deliver through bounded concurrent workers. Parameters ---------- hub : type[Hub] Hub namespace restricting every recipient. connection_ids : tuple[str, ...] Recipient identifiers selected by the application. envelope : object Typed or mapping envelope accepted by the selected Hub codecs. Returns ------- BroadcastResult Successful and failed recipient counts; cancellation propagates. Raises ------ TypeError, ValueError If the payload cannot be encoded before delivery begins. |
| Hub | from orionis.realtime import Hub | [hub.py](../hub.py) | Hub | Define an invocation-scoped realtime endpoint with explicit remote methods. |
| Hub.onConnect | from orionis.realtime import Hub | [hub.py](../hub.py) | async def onConnect(self) -> None | Run connection initialization before the ready envelope is sent. Returns ------- None A subclass may reject or initialize this connection. |
| Hub.onDisconnect | from orionis.realtime import Hub | [hub.py](../hub.py) | async def onDisconnect(self, code: int, reason: str / None) -> None | Run after connection-owned calls and registrations are released. Parameters ---------- code : int Observed close code, or an abnormal closure when unavailable. reason : str / None, optional Available peer or local close reason. Returns ------- None A subclass may release application-owned connection resources. |
| HubClients | from orionis.realtime import HubClients | [clients.py](../clients.py) | HubClients | Select ready clients within one Hub in the current worker. |
| HubClients.all | from orionis.realtime import HubClients | [clients.py](../clients.py) | def all(self) -> ClientTarget | Return a target for every ready connection to this Hub. Returns ------- ClientTarget Target resolving ready Hub connections at delivery time. |
| HubClients.caller | from orionis.realtime import HubClients | [clients.py](../clients.py) | def caller(self) -> ClientTarget | Return a target for the calling connection. Returns ------- ClientTarget Single-client target supporting event delivery and invocation. Raises ------ RuntimeError If this proxy was created outside a Hub connection. ValueError If the caller identifier is invalid. |
| HubClients.others | from orionis.realtime import HubClients | [clients.py](../clients.py) | def others(self) -> ClientTarget | Return a target excluding the calling connection. Returns ------- ClientTarget Target resolving other ready Hub connections at delivery time. Raises ------ RuntimeError If this proxy was created outside a Hub connection. |
| HubClients.client | from orionis.realtime import HubClients | [clients.py](../clients.py) | def client(self, connection_id: str) -> ClientTarget | Select one connection for event delivery or bidirectional invocation. Parameters ---------- connection_id : str Identifier belonging to a connection in this Hub. Returns ------- ClientTarget Single recipient target; unavailable recipients fail on delivery. Raises ------ ValueError If the identifier is empty, non-string or longer than 128 characters. |
| HubClients.clients | from orionis.realtime import HubClients | [clients.py](../clients.py) | def clients(self, connection_ids: Iterable[str]) -> ClientTarget | Select explicit recipients, preserving order and removing duplicates. Parameters ---------- connection_ids : Iterable[str] Connection identifiers belonging to this Hub. Returns ------- ClientTarget Multi-recipient target supporting event delivery. Raises ------ TypeError If the input is a string, bytes or a noniterable value. ValueError If any identifier is invalid. |
| HubClients.group | from orionis.realtime import HubClients | [clients.py](../clients.py) | def group(self, name: str) -> ClientTarget | Select a named group within this Hub namespace. Parameters ---------- name : str Nonempty group name, at most 256 characters. Returns ------- ClientTarget Target resolving current group membership at delivery time. Raises ------ ValueError If the name is empty, non-string or longer than 256 characters. |
| HubContext | from orionis.realtime import HubContext | [hub.py](../hub.py) | HubContext | Expose connection identity without providing service location. |
| HubGroups | from orionis.realtime import HubGroups | [groups.py](../groups.py) | HubGroups | Manage group membership owned by the current Hub connection. |
| HubGroups.join | from orionis.realtime import HubGroups | [groups.py](../groups.py) | async def join(self, group: str) -> None | Join a group without consuming another slot for existing membership. Parameters ---------- group : str Hub-local group name, at most 256 characters. Returns ------- None Add the current connection, subject to its configured group limit. Raises ------ ValueError If the group name is invalid. ConnectionError If the connection is absent or closing. RuntimeError If another membership would exceed the configured group limit. |
| HubGroups.leave | from orionis.realtime import HubGroups | [groups.py](../groups.py) | async def leave(self, group: str) -> None | Remove the current connection from one group idempotently. Parameters ---------- group : str Hub-local group name. Returns ------- None Remove membership and discard groups with no remaining members. Raises ------ ValueError If the group name is invalid. |
| HubProtocol | from orionis.realtime import HubProtocol | [protocol.py](../protocol.py) | HubProtocol | Encode Orionis Realtime v1 using route-selected JSON or MessagePack. |
| HubProtocol.decode | from orionis.realtime import HubProtocol | [protocol.py](../protocol.py) | def decode(self, message: WebSocketMessage) -> ClientMessage | Decode and validate one client envelope from a complete socket message. Parameters ---------- message : WebSocketMessage Text JSON or binary MessagePack message selected by the route. Returns ------- ClientMessage Strict typed request, completion, cancellation or ping/pong. Raises ------ ProtocolError If frame kind, size, fields or structural limits are invalid. |
| HubProtocol.encode | from orionis.realtime import HubProtocol | [protocol.py](../protocol.py) | def encode(self, message: object) -> str / bytes | Encode an outgoing envelope once for direct send or broadcast reuse. Parameters ---------- message : object Framework-owned envelope containing a serializable result or event. Returns ------- str / bytes Text JSON or binary MessagePack payload. Raises ------ TypeError If an application result cannot be encoded. |
| remote | from orionis.realtime import remote | [decorators.py](../decorators.py) | def remote(function: F, *, name: str / None) -> F | Mark a supplied instance method for remote dispatch. Parameters ---------- function : F Original instance-method function. name : str / None, optional Public alias, or None to use the Python method name. Returns ------- F Original function with validated remote metadata attached. Raises ------ TypeError If the supplied object is not a Python function. ValueError If the method name or alias is invalid, or metadata is already attached. |

## Usage examples

    from orionis.realtime import BroadcastResult

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
