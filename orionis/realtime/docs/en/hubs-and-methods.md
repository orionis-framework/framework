# Building a hub with typed operations

Use a Hub to group operations sharing an audience and protocol. Only ordinary instance methods marked `@remote` are callable remotely. A public method without the decorator remains outside the remote surface.

```python
import asyncio
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub

class MathHub(Hub):
    @remote(name="sum")
    async def add(self, first: int, second: int = 2) -> int:
        return first + second

methods = compile_hub(MathHub)
assert asyncio.run(methods["sum"].bind([3], {})) == {"first": 3, "second": 2}
```

This example compiles without a server. Serve it through `Route.hub("/realtime/math", MathHub)`, importing Route from `orionis.support.facades`. `protocol="msgpack"` selects binary MessagePack for the whole connection; JSON text is default. Codecs are not negotiated per message.

## Data and services

Annotate every remote argument. Msgspec-compatible data types convert client arguments; service types resolve through the container and cannot be replaced by payload values. Nested Orionis schemas, including those inside collections or plain structs, run their synchronous or asynchronous rules before dispatch. Direct calls to `bind()` must be awaited; inside an existing event loop use `await methods["sum"].bind([3], {})`. Defaults and keyword-only parameters are supported.

For an importable application `Calculator` service, a method can declare `async def add(self, first: int, calculator: Calculator, second: int = 2) -> int`. Register/resolve Calculator normally. Keep imports available at runtime when reflection requires them; do not hide every injectable annotation under `TYPE_CHECKING` without a resolution strategy.

Compilation rejects private names, duplicate aliases, class/static methods, positional-only parameters, variadics and ambiguous annotations. Aliases must be public Python identifiers of at most 128 characters. A registration failure is preferable to exposing a signature with unclear input ownership.

## Context and lifecycle

Each invocation receives a fresh instance with `context`, `clients` and `groups`. `context.connection_id` identifies the connection, `.socket` exposes WebSocket and `.user` contains the pipeline-established identity. Do not use instance attributes to retain state between calls; use domain services or an appropriate registry.

`onConnect()` runs after registration and before readiness; it may join groups or reject setup. `onDisconnect(code, reason)` runs after owned work is cancelled and registration removed. Release application resources idempotently. The decorator controls exposure rather than permission; authorize individual operations as well as the handshake where needed.

## Deliberate failures

For a client-visible business condition, import `RPCError` from `orionis.realtime.errors` and raise `RPCError("conflict", "Operation is no longer available")`. The runtime sanitizes internal, validation, authorization, timeout and cancellation failures into stable codes. Do not expose tracebacks or provider errors as public messages.

Evidence: [Hub](../../hub.py), [decorator](../../decorators.py), [compilation](../../metadata.py), [runtime](../../runtime.py). Tests: [metadata](../../../../tests/realtime/test_metadata.py), [kernel](../../../../tests/realtime/test_kernel.py), [runtime](../../../../tests/realtime/test_runtime.py). Continue with [protocol](protocol-and-streaming.md).
