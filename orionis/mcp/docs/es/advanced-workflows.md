# Progreso, continuación, suscripciones y extensiones

Estas capacidades permiten flujos más largos que una llamada simple, manteniendo cada petición independiente. Diseña efectos de negocio de forma explícita: el transporte no aporta transacciones distribuidas, entrega durable ni reintentos idempotentes por sí mismo.

## Progreso con salida final

```python
from orionis.mcp import McpResponse, Tool

class ReportTool(Tool):
    async def handle(self):
        yield McpResponse.progress(0, total=2, message="Starting")
        yield McpResponse.progress(1, total=2, message="Collecting")
        yield McpResponse.text("Report ready")
```

El handler es un generador asíncrono. Las actualizaciones se convierten en `notifications/progress` solo cuando la llamada contiene `progressToken`; sin opt-in se omiten. Los números deben ser finitos y el avance debe aumentar estrictamente. Los demás elementos se reúnen y normalizan en el resultado final, dentro de `MCP_MAX_RESPONSE_SIZE`; este flujo no es un stream ilimitado de resultados parciales. Usa `try/finally` para recursos y deja propagarse cancelación.

## Solicitar datos adicionales y continuar

Un handler puede devolver `InputRequiredResult(inputRequests=..., requestState=...)`. El cliente resuelve los inputs y vuelve a llamar con `inputResponses`/`requestState`; no existe un hilo de servidor suspendido esperando memoria de la llamada anterior. Las operaciones admitidas para inputs son `elicitation/create`, `sampling/createMessage` y `roots/list`, condicionadas a capacidades de esta petición.

```python
from orionis.mcp import InputRequiredResult, McpRequest, McpResponse, Tool

class ConfirmTool(Tool):
    async def handle(self, request: McpRequest):
        if request.input_responses:
            return McpResponse.text("Response received; validate before acting")
        return InputRequiredResult(inputRequests={
            "choice": {"method": "elicitation/create", "params": {
                "message": "Choose a label",
                "requestedSchema": {"type": "object", "properties": {
                    "label": {"type": "string"}
                }},
            }},
        })
```

El ejemplo demuestra estructura, no ejecuta una acción al recibir cualquier respuesta. Antes de actuar comprueba clave, acción y contenido validados; una respuesta decline/cancel no es aceptación. Las formas de elicitation admiten un objeto plano de campos primitivos, no un schema arbitrario anidado. Anuncia capacidades compatibles en `_meta` del cliente; una petición que no las declare falla antes de pedir datos.

Para estado confiable utiliza `McpState.seal(request, value, ttl=300)` y `open(request)`. Requiere `app.cipher` AES-128-GCM o AES-256-GCM; autentica/cifra el estado y lo vincula a principal, servidor confiable, método, argumentos y expiración. Workers deben compartir clave/cipher. El servidor descifra/valida antes de usarlo; copiar `requestState` sin verificar no convierte datos del cliente en datos confiables. No se implementa prevención general de replay de efectos: coordina idempotencia en almacenamiento de dominio.

## Suscribirse a cambios

Declara `Server.list_changed=True` para cambios de catálogos y `resource_subscriptions=True` para recursos. El cliente abre `subscriptions/listen` con un filtro `notifications` que contiene `toolsListChanged`, `promptsListChanged`, `resourcesListChanged` o `resourceSubscriptions`. Acceso a cada URI se verifica al admitir la suscripción y durante el flujo según dispatcher.

Después de modificar el catálogo llama `await Mcp.toolsChanged(ServerClass)`, `promptsChanged`, `resourcesChanged` o `resourceUpdated(ServerClass, uri)`. La clase debe estar registrada en ese manager. Las notificaciones pertenecen a listeners de ese servidor. El bus predeterminado es local al proceso, con buffers y cantidad de subscripciones acotados; no ofrece entrega entre workers ni replay. Cierra streams y listeners en desconexión/shutdown.

En pruebas usa `McpTestClient.stream(...)` para suscripciones; `request(...)` reúne un intercambio finito y esperaría indefinidamente un stream vivo. El cliente mantiene scope hasta consumir/cerrar stream.

## Catálogos de herramientas grandes

`Server.tools = (ToolCatalog(ToolA, ToolB),)` expone `search_tools` y `execute_tools`; los nombres son personalizables. Search recibe `query` y `limit`, ejecuta políticas por petición y devuelve metadata con schemas. Execute recibe `calls=[{"name": ..., "arguments": ...}]`, comprueba cada operación y limita número/salida. Las llamadas se ejecutan secuencialmente, no como transacción atómica. Si una necesita input, ejecútala individualmente; no repitas efectos ya completados de un batch.

## Extender métodos del protocolo

`McpExtension(identifier=..., capabilities=..., methods=..., decoders=..., schema_hook=...)` registra capacidades y handlers de extensión. El cliente debe negociar el identificador. Los hooks pueden adjuntar metadata de extensión, pero no cambiar nombres, schemas, URI, MIME u otros campos estándar ya compilados ni claves reservadas. Usa namespace propio y decoders tipados; una extensión no debe eludir validación del núcleo.

Evidencia: [dispatcher](../../dispatcher.py), [MRTR](../../protocol/mrtr.py), [estado](../../state.py), [bus](../../subscriptions/event_bus.py), [catálogo](../../server/catalog.py), [extensiones](../../server/extension.py). Pruebas: [streams](../../../../tests/mcp/test_streams.py), [estado](../../../../tests/mcp/test_state.py), [eventos](../../../../tests/mcp/test_event_bus.py), [auditoría](../../../../tests/mcp/test_audit_edges.py). Revisa [presupuestos](transports-and-configuration.md).
