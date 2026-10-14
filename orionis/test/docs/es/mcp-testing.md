# Probar herramientas MCP dentro del proceso

El cliente MCP envía JSON-RPC codificado al dispatcher real y abre un scope nuevo por llamada. Es una prueba de integración del protocolo y del contenedor, sin sockets. No sustituye una prueba de un proxy HTTP, origen autorizado o transporte stdio. La declaración del servidor siguiente pertenece al módulo de prueba y se ejecuta bajo el runner de Orionis.

## Ejemplos

### Ejercitar una herramienta MCP real

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

## Fuentes y siguientes pasos

[mcp.py](../../clients/mcp.py) · [case.py](../../cases/case.py)

[Volver al índice del módulo](README.md).
