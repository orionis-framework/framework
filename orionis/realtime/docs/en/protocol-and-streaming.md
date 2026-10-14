# Protocol, streams and bidirectional results

Protocol v1 uses envelopes with a `type` field. Clients must await `ready`, correlate identifiers and distinguish ordinary results from streams and events. JSON uses WebSocket text; MessagePack uses bytes. Sending the wrong frame type is a protocol error.

## Calling and cancelling

```json
{"type":"invoke","id":"call-1","target":"sum","args":[2,3],"kwargs":{}}
```

Scalar responses arrive as `completion` with the same ID and a result or error. Cancel an active call with:

```json
{"type":"cancel","id":"call-1"}
```

IDs are printable ASCII without spaces, at most 128 characters. Args and kwargs are each limited to 64 entries. Do not reuse an active ID. Client completions must contain exactly one result or error; an explicit `null` result is valid. Unknown and duplicate completions are not retained.

## Producing a sequence

```python
from collections.abc import AsyncIterator
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub

class FeedHub(Hub):
    @remote
    async def updates(self, count: int) -> AsyncIterator[int]:
        for value in range(count):
            yield value

assert compile_hub(FeedHub)["updates"].is_stream
```

The runtime delivers `stream_item` followed by `stream_complete`. Iteration follows socket pace. Use `try/finally` in resource-owning generators; cancellation/disconnection must close the iterator before releasing its scope. Streams have no default lifetime timeout; an explicit invoke `timeout` limits the operation. Scalar calls use `REALTIME_INVOCATION_TIMEOUT` unless overridden.

## Requesting a client result

Within a hub, `await self.clients.caller.invoke("confirm", payload, timeout=5.0)` sends an invocation and awaits its correlated completion; `payload` must be a serializable value prepared by your method. This also works on `clients.client(id)`. Multi-recipient targets cannot `invoke` because there is no single result to correlate. Use `send` for events without a returned result.

The connection reader remains available while awaiting results, which may arrive out of order. Pending calls have bounded capacity and deadlines. Client errors become sanitized `ClientInvocationError`; arbitrary peer text is not copied into internal diagnostics.

## Closing and compatibility

Invalid protocol closes with 1002, wrong frame type with 1003 and excessive size with 1009. Application ping/pong is available; it provides neither persistence nor an automatic heartbeat task. Clients should release pending callbacks on disconnect and reconcile state on reconnect: automatic replay is not provided.

Evidence: [protocol](../../protocol.py), [connection](../../connection.py), [runtime](../../runtime.py). Tests: [wire](../../../../tests/realtime/test_protocol.py), [correlation](../../../../tests/realtime/test_connection.py), [streams](../../../../tests/realtime/test_runtime.py). Continue with [groups and deployment](groups-and-deployment.md).
