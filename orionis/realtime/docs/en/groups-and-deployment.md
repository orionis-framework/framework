# Groups, broadcasts and deployment

Groups select connections belonging to a Hub, such as room participants. They are not security roles: authorize access before joining. Membership disappears on disconnect and is not a durable subscription.

```python
from orionis.realtime import Hub, remote

class RoomHub(Hub):
    @remote
    async def join(self, room: str) -> None:
        if self.context.user is None:
            from orionis.realtime.errors import RPCError
            raise RPCError("unauthenticated", "Sign in first")
        await self.groups.join(room)
        await self.clients.group(room).send("joined", self.context.connection_id)
```

This example checks identity, but private rooms also need domain authorization for the requested name. A client-controlled name is not proof of membership. `groups.leave(name)` leaves a group. Identifiers/groups are validated for bounded size and content.

## Selecting recipients

`clients.all`, `.caller` and `.others` are properties; `.client(id)`, `.clients(ids)` and `.group(name)` are methods. Every target supports `await target.send(event, *args)`. `.caller` and `.others` require an invocation caller. From controllers/jobs use `Realtime.hub(RoomHub).all.send(...)`, importing Realtime from `orionis.support.facades`; that selection has no caller.

```python
import asyncio
from orionis.realtime import ConnectionManager
from orionis.realtime.config import RealtimeConfig
from orionis.realtime import Hub

class EmptyHub(Hub):
    pass

async def example():
    manager = ConnectionManager(RealtimeConfig())
    result = await manager.hub(EmptyHub).all.send("refresh", {"version": 1})
    assert (result.sent, result.failed) == (0, 0)

asyncio.run(example())
```

`BroadcastResult.sent` counts transport delivery and `failed` counts failed recipients; it does not acknowledge client code execution. Broadcasts snapshot IDs and recheck availability before writing. Concurrent disconnects may appear as failures.

## Execution budgets

| Variable | Default |
|---|---:|
| `REALTIME_MAX_MESSAGE_SIZE` | 1 MiB |
| `REALTIME_MAX_CONCURRENT_INVOCATIONS` | 16 per connection |
| `REALTIME_MAX_PENDING_CLIENT_INVOCATIONS` | 32 per connection |
| `REALTIME_INVOCATION_TIMEOUT` | 30 seconds, scalar |
| `REALTIME_CLIENT_RESULT_TIMEOUT` | 30 seconds |
| `REALTIME_BROADCAST_CONCURRENCY` | 32 concurrent deliveries |
| `REALTIME_MAX_GROUPS_PER_CONNECTION` | 64 |

Budgets are positive integers and timeouts are finite positive values. `config/realtime.py` constructs `RealtimeConfig`; the provider registers immutable configuration. Combine them with HTTP WebSocket message/connection limits. Raising a Realtime limit does not automatically raise the transport limit.

## Workers, ordering and extension

`ConnectionManager` and groups are worker-local. Processes do not see each other's connections; restart loses registrations/membership. Cross-worker delivery needs an application backplane and compatible `IConnectionManager` implementation. Configuring Redis elsewhere does not automatically add pub/sub or offline storage.

Connections serialize writes under a lock and apply backpressure; a failed write closes the connection and cancels its owner to prevent later writes overtaking it. Broadcasts bound fan-out and encode once per codec. Access the manager on the application's event loop; it is not a globally thread-safe registry.

Remote reflection caches up to 1024 Hub classes. Instances/scopes remain invocation-specific. Do not retain scoped resources in tasks that outlive connections; manage cancellation, joining and closure of your own tasks.

Evidence: [clients](../../clients.py), [groups](../../groups.py), [manager](../../manager.py), [contract](../../contracts/manager.py), [config](../../../../config/realtime.py). Tests: [manager](../../../../tests/realtime/test_manager.py), [connections](../../../../tests/realtime/test_connection.py), [metadata](../../../../tests/realtime/test_metadata.py). See [WebSocket](../../../http/docs/en/websockets.md) for handshake limits.
