# Building a server with typed tools

Tools receive contract-defined data and return content or typed values. Perform work through injected services; `Server`/`Tool` declarations hold static metadata, not mutable state from earlier calls.

## A complete tool and a network-free test

```python
import asyncio
from orionis.container.container import Container
from orionis.mcp import McpResponse, Server, Tool, ToolAnnotations
from orionis.mcp.server.compiler import compile_server
from orionis.schemas import Schema
from orionis.test import McpTestClient

class GreetInput(Schema):
    name: str

class GreetTool(Tool[GreetInput, str]):
    description = "Return a greeting."
    annotations = ToolAnnotations(read_only=True, destructive=False)

    def handle(self, payload: GreetInput) -> McpResponse:
        return McpResponse.structured(f"Hello, {payload.name}!")

class DemoServer(Server):
    name = "Demo"
    version = "1.0.0"
    tools = (GreetTool,)

assert tuple(compile_server(DemoServer).tools) == ("greet",)

async def example():
    client = McpTestClient(Container(), DemoServer)
    result = await client.tool("greet", {"name": "Ada"})
    result.assertOk()
    result.assertTextContains("Hello, Ada!")

asyncio.run(example())
```

Inferred names remove primitive suffixes and use kebab-case. Set `name` for a stable contract. Explicit names match `[A-Za-z0-9_.-]{1,128}`; duplicate names and invalid metadata fail compilation. Subclass `Tool`; it is not configured through `Tool(name=..., handler=...)`.

## Input, output and injection

`Tool[Input, Output]` declares validation and JSON Schema; `input` and `output` attributes are also available. Handlers may be synchronous or asynchronous. Orionis converts payloads, validates schemas and separately resolves services and `McpRequest`. Client keys cannot replace injected services with matching names.

Declared output is validated before serialization. Return `McpResponse.structured(value)` containing a compatible value; handlers must return `McpResponse` or response sequences rather than raw strings/dicts. Contract failures become protocol failures. Do not promise a response structure incompatible with the generic output type. The test client passes bytes through the dispatcher, exercising actual serialization rather than calling the method directly.

## Availability and authorization

Add `shouldRegister(self, request: McpRequest) -> bool` for request-specific visibility and `authorize(...) -> bool` for access. The actual hook name is **shouldRegister**, not `available`. Both run during listing and direct invocation; hiding a tool does not leave an unchecked direct path.

`request.identity` and `request.authentication` expose context identity; `client_capabilities` contains only this call's declarations. Requests are immutable snapshots, including nested mappings. Injected services retain their own concurrency rules; do not retain calls in singleton services.

`ToolAnnotations` describes read-only, destructive, idempotent and open-world behavior. These are client hints: they do not authorize actions or make transactions idempotent. Return `McpResponse.error(message)` for expected business failures; unexpected failures are sanitized before reaching clients.

## Application registration

During application boot use `Mcp.web("/mcp/demo", DemoServer)` or `Mcp.local("demo", DemoServer)`, importing Mcp from `orionis.support.facades`. The manager compiles once per class and retains immutable definitions; handlers are constructed in call scopes. Read [transports](transports-and-configuration.md) for headers and endpoint protection.

Evidence: [primitives](../../server/primitives.py), [compiler](../../server/compiler.py), [invoker](../../invoker.py), [dispatcher](../../dispatcher.py), [test client](../../../test/clients/mcp.py). Tests: [compiler](../../../../tests/mcp/server/test_compiler.py), [invoker](../../../../tests/mcp/server/test_invoker.py), [dispatcher](../../../../tests/mcp/test_dispatcher.py).
