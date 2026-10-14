# Testing MCP tools in process

The MCP client sends encoded JSON-RPC through the real dispatcher and opens a new scope for each call. It integrates the protocol and container without sockets. It does not replace testing an HTTP proxy, allowed origin, or stdio transport. The following server declaration belongs in the test module and runs through the Orionis runner.

## Examples

### Exercise a real MCP tool

```python
from orionis.mcp import McpResponse, Server, Tool
from orionis.schemas import Schema
from orionis.test import TestCase

class GreetingInput(Schema):
    name: str

class HelloTool(Tool[GreetingInput]):
    name = "hello"

    def handle(self, payload: GreetingInput) -> McpResponse:
        return McpResponse.text(f"Hello, {payload.name}")

class GreetingServer(Server):
    name = "greetings"
    tools = (HelloTool,)

class TestGreetingServer(TestCase):
    async def testHello(self) -> None:
        client = await self.mcp(GreetingServer)
        response = await client.tool("hello", {"name": "Ada"})
        response.assertOk()
        response.assertTextContains("Hello, Ada")
```

## Evidence and next steps

[mcp.py](../../clients/mcp.py) · [case.py](../../cases/case.py)

[Return to the module index](README.md).
