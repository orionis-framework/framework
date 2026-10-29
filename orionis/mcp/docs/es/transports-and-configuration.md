# Transportes HTTP, STDIO y configuración

Registra una clase Server durante el boot con la facade `Mcp`. `web(path, server)` crea una ruta POST API nativa y devuelve su builder; admite paths fijos sin parámetros, query ni fragmento. `local(name, server)` registra un handle explícito con letras, dígitos, punto, guion o underscore. No permite iniciar módulos arbitrarios por nombre proporcionado por un cliente.

```python
from orionis.mcp import McpResponse, Server, Tool
from orionis.schemas import Schema
from orionis.support.facades import Mcp

class GreetInput(Schema):
    name: str

class GreetTool(Tool[GreetInput, str]):
    def handle(self, payload: GreetInput) -> McpResponse:
        return McpResponse.structured(f"Hello, {payload.name}!")

class ApplicationServer(Server):
    name = "Application"
    tools = (GreetTool,)

Mcp.web("/mcp/application", ApplicationServer)
Mcp.local("application", ApplicationServer)
```

Este bloque necesita una aplicación inicializada. Añade middleware API de autenticación al builder web cuando todo el servidor deba estar protegido. La resolución de identidad no exige automáticamente credenciales; los hooks `authorize` siguen protegiendo operaciones.

## Contrato HTTP real

El transporte exige POST, un único `Content-Type: application/json` y Accept que incluya explícitamente `application/json` y `text/event-stream` con calidad positiva. Una respuesta finita utiliza JSON; progreso/suscripción puede usar SSE. El protocolo de este checkout refleja metadata del envelope en cabeceras:

```http
POST /mcp/application HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
MCP-Method: tools/call
MCP-Name: greet
```

El cuerpo correspondiente reutiliza la herramienta del [primer capítulo](servers-and-tools.md):

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"greet","arguments":{"name":"Ada"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}
```

El protocolo exige coincidencia entre cabeceras y cuerpo para versión, método y nombre/URI de primitivas. Los parámetros anotados `x-mcp-header` requieren además cabeceras `MCP-Param-<name>` compatibles; solo se permiten propiedades primitivas alcanzables estáticamente. Datos binarios/MIME de un recurso no cambian el Content-Type JSON del envelope.

Una cabecera Origin ausente está permitida. Si aparece debe coincidir exactamente con `allowed_origins`, lista de orígenes HTTP(S) validados. No hay wildcard ni excepción implícita de mismo origen. Bootstrap utiliza `CORS_ALLOW_ORIGINS`; CORS HTTP o WebSocket pueden tener reglas diferentes. Se rechaza origen, método o media type antes de leer un cuerpo grande.

`allowed_origins` utiliza una `list[str]` independiente por instancia. Si
`CORS_ALLOW_ORIGINS` no está definida, el archivo editable
[config/mcp.py](../../../../config/mcp.py) proporciona el origen del inspector MCP de
Orionis. El núcleo `McpConfig` conserva `[]` como predeterminado, sin incorporar URLs
de la aplicación. Define la variable de entorno o edita la lista del bootstrap para
reemplazar ese valor; una lista vacía explícita rechaza cualquier Origin presente.
Cada entrada contiene solo esquema, host y puerto opcional, sin ruta ni barra final.

## STDIO y consola

Inicia un handle registrado con `python -B reactor mcp:start application`; `python -B reactor mcp:list` muestra servidores. Los generadores son `make:mcp-server`, `make:mcp-tool`, `make:mcp-resource` y `make:mcp-prompt`. Los comandos se ejecutan en el contexto de la aplicación configurada.

STDIO usa mensajes JSON por línea; stdout se reserva exclusivamente para frames y diagnósticos van a stderr. El transporte acota lectura y concurrencia, admite cancelación por notificación y usa el mismo dispatcher que HTTP. No imprimas logging convencional en stdout dentro de handlers.

## Presupuestos

| Variable | Predeterminado |
|---|---:|
| `MCP_MAX_REQUEST_SIZE` | `HTTP_MAX_BODY_SIZE` o 1 MiB |
| `MCP_MAX_CONCURRENT_REQUESTS` | `HTTP_MAX_CONCURRENT_REQUESTS` o 32 |
| `MCP_DEFAULT_PAGE_SIZE`, `MCP_MAX_PAGE_SIZE` | 50, 100 |
| `MCP_MAX_RESPONSE_SIZE`, `MCP_MAX_METADATA_SIZE` | 4 MiB, 64 KiB |
| `MCP_SUBSCRIPTION_BUFFER_SIZE`, `MCP_MAX_SUBSCRIPTIONS` | 64, 1024 |
| `MCP_MAX_RESOURCE_SUBSCRIPTIONS` | 64 |
| `MCP_SUBSCRIPTION_KEEPALIVE` | 15 segundos |
| `MCP_TOOL_SEARCH_MAX_RESULTS`, `MCP_TOOL_SEARCH_MAX_CALLS` | 20, 5 |
| `MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES` | 256 KiB |

Todos los presupuestos numéricos son positivos y página default no puede superar máximo. La admisión del transporte incluye streams hasta cerrarlos. El manager ofrece `getWebServer`, `getLocalServer`, `servers`, `dispatchHttp`, `startLocal` y `shutdown`; normalmente la integración administra dispatch/cierre. Sobrecarga, request inválido y respuesta demasiado grande fallan de forma explícita, sin cola ilimitada.

Evidencia: [manager](../../manager.py), [HTTP](../../transport/http.py), [cabeceras](../../transport/headers.py), [STDIO](../../transport/stdio.py), [config](../../../../config/mcp.py). Pruebas: [HTTP](../../../../tests/mcp/transport/test_http.py), [cabeceras](../../../../tests/mcp/transport/test_headers.py), [STDIO](../../../../tests/mcp/transport/test_stdio.py), [desconexión](../../../../tests/mcp/transport/test_disconnect.py).
