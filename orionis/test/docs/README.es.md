# orionis.test

> Referencia de API derivada de la implementación actual.

## Tabla de contenido

- Requisitos
- Resumen funcional
- Estructura del módulo
- Referencia de API
- Ejemplos de uso
- Características de diseño
- Rendimiento y concurrencia
- Notas de compatibilidad
- Verificación y limitaciones

## Requisitos

Python 3.14 o superior, como declara pyproject.toml.

## Resumen funcional

El inicializador de orionis.test expone 3 símbolos públicos. Esta referencia usa __all__, las rutas de exportación y los archivos fuente actuales como evidencia.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| ../__init__.py | Define las exportaciones del paquete. |
| orionis.test/ | Implementaciones y subpaquetes de esas exportaciones. |

## Referencia de API

| Símbolo | Importación verificada | Fuente | Declaración | Comportamiento observado |
| --- | --- | --- | --- | --- |
| McpTestClient | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | McpTestClient | Open scopes on the supplied container; never create a parallel application. |
| McpTestClient.stream | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | async def stream(self, method: str, params: dict[str, object] / None, *, meta: dict[str, object] / None, request_id: str / int) -> AsyncIterator[dict[str, object]] | Keep the existing application's scope alive through the entire stream. Parameters ---------- method : str Value supplied for ``method``. params : dict[str, object] / None Parameters decoded for the requested operation. meta : dict[str, object] / None Value supplied for ``meta``. request_id : str / int Value supplied for ``request_id``. Yields ------ dict[str, object] Each item produced by the documented iteration. |
| McpTestClient.request | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | async def request(self, method: str, params: dict[str, object] / None, *, meta: dict[str, object] / None, request_id: str / int) -> McpTestResponse | Collect a finite exchange; use stream() for subscriptions. Parameters ---------- method : str Value supplied for ``method``. params : dict[str, object] / None Parameters decoded for the requested operation. meta : dict[str, object] / None Value supplied for ``meta``. request_id : str / int Value supplied for ``request_id``. Returns ------- McpTestResponse Result of the operation described above. |
| McpTestClient.tool | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | async def tool(self, name: str, arguments: dict[str, object] / None) -> McpTestResponse | Invoke a tool through JSON-RPC input and output bytes. Parameters ---------- name : str Value supplied for ``name``. arguments : dict[str, object] / None Arguments supplied for this operation. Returns ------- McpTestResponse Result of the operation described above. |
| McpTestResponse | from orionis.test import McpTestResponse | [clients/mcp.py](../clients/mcp.py) | McpTestResponse | Decoded result and notifications from a complete wire round trip. |
| McpTestResponse.assertOk | from orionis.test import McpTestResponse | [clients/mcp.py](../clients/mcp.py) | def assertOk(self) -> None | Require a successful protocol and tool result. Returns ------- None Complete the documented operation without returning a value. |
| McpTestResponse.assertTextContains | from orionis.test import McpTestResponse | [clients/mcp.py](../clients/mcp.py) | def assertTextContains(self, text: str) -> None | Check returned tool text without bypassing response serialization. Parameters ---------- text : str Value supplied for ``text``. Returns ------- None Complete the documented operation without returning a value. |
| TestCase | from orionis.test import TestCase | [cases/case.py](../cases/case.py) | TestCase | Exported public constant or alias. |
| TestCase.setMethodPattern | from orionis.test import TestCase | [cases/case.py](../cases/case.py) | def setMethodPattern(cls, pattern: str) -> None | Set the method pattern for identifying test methods. Parameters ---------- pattern : str The glob pattern to match test method names (e.g., "test*"). Returns ------- None This method stores the compiled pattern in the current context and returns None. |
| TestCase.mcp | from orionis.test import TestCase | [cases/case.py](../cases/case.py) | async def mcp(self, server: type[Server] / CompiledMcpServer, config: McpConfig / None, *, app: IContainer / None) -> McpTestClient | Create an MCP client using the test runner's application. Parameters ---------- server : type[Server] / CompiledMcpServer Server declaration or compiled snapshot to exercise. config : McpConfig / None, optional Client limits; use MCP defaults when omitted. app : IContainer / None, optional Explicit container for isolated tests; otherwise use the application already booted by the Orionis test runner. Returns ------- McpTestClient In-process client with independent request scopes and event state. Raises ------ RuntimeError If no container is supplied and the application is not booted. |

## Ejemplos de uso

    from orionis.test import McpTestClient

La ruta de importación coincide con la tabla de API. Estado de importación: executed successfully under Python 3.14.3.

## Características de diseño

El paquete utiliza una superficie pública explícita. Los símbolos privados no se incluyen; las declaraciones se enlazan al propietario concreto.

## Rendimiento y concurrencia

No se declara una garantía uniforme en el nivel del paquete. Inspeccione cada archivo enlazado para E/S, corutinas, cachés, bloqueos y estado compartido.

## Notas de compatibilidad

Mínimo declarado: Python 3.14. La validación usó Python 3.14.3. Los límites de dependencias están en pyproject.toml.

## Verificación y limitaciones

Se analizaron los archivos Python y se verificaron las exportaciones. Las excepciones de dependencias, callbacks, E/S o configuración pueden propagarse y no se presentan como exhaustivas.
