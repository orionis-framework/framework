# orionis.mcp

> `orionis.mcp` proporciona servidores nativos, tipados e independientes del transporte para Model Context Protocol en aplicaciones Orionis.

## Descripción general

El paquete declara herramientas, recursos, prompts y servidores como clases de Python. Orionis valida y compila esas declaraciones una sola vez y expone la misma definición inmutable mediante HTTP, STDIO, inyección de dependencias, la fachada `Mcp` y el cliente de pruebas. La versión implementada del protocolo es `2026-07-28`.

El runtime aísla el contexto de cada solicitud, valida entradas JSON-RPC y esquemas tipados, aplica límites de concurrencia y tamaño de respuesta, y admite progreso, elicitación, completion, suscripciones, paginación, indicaciones de caché y métodos de extensión.

## Requisitos

- Python 3.14 o posterior.
- Una aplicación Orionis iniciada para registro de transportes, inyección, autenticación y la fachada `Mcp`.
- Tipos de entrada/salida compatibles con los esquemas de Orionis y `msgspec` al usar herramientas tipadas.
- Orígenes confiables explícitos cuando clientes de navegador envían el encabezado HTTP `Origin`.

## Inicio rápido

```python
from orionis.mcp import McpResponse, Server, Tool, ToolAnnotations
from orionis.mcp.server.compiler import compile_server
from orionis.schemas import Schema


class GreetInput(Schema):
    name: str


class GreetTool(Tool[GreetInput, str]):
    description = "Return a greeting."
    annotations = ToolAnnotations(read_only=True, destructive=False)

    def handle(self, payload: GreetInput) -> str:
        return f"Hello, {payload.name}!"


class DemoServer(Server):
    name = "Demo"
    version = "1.0.0"
    tools = (GreetTool,)


compiled = compile_server(DemoServer)
assert tuple(compiled.tools) == ("greet",)
assert McpResponse.text("ready").content[0].text == "ready"
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

## Conceptos principales

### Declaraciones y compilación

`Tool`, `Resource`, `Prompt` y `Server` contienen metadatos estáticos y métodos manejadores. `compile_server()` deriva nombres kebab-case, compila esquemas y planes de inyección, valida metadatos y plantillas URI, y produce un `CompiledMcpServer` reutilizable. Las instancias de manejadores pertenecen a la solicitud; las declaraciones no deben guardar estado mutable de solicitudes.

### Contexto de solicitud

`McpRequest` (también exportado como `McpContext`) es una instantánea congelada con id y método JSON-RPC, id del servidor, metadatos, argumentos, parámetros, variables URI, transporte, contexto de autenticación y solicitud HTTP nativa opcional. Los mappings anidados del cliente quedan de solo lectura. `identity` delega a la autenticación de Orionis y `client_capabilities` solo lee la solicitud actual.

### Respuestas y errores de protocolo

`McpResponse` construye resultados de texto, imagen, audio, recurso embebido, enlace, datos estructurados, error y progreso sin conocer el transporte. Los fallos visibles para una herramienta usan `McpResponse.error()`; JSON-RPC mal formado, argumentos inválidos, fallos de autorización y fallos internos usan las excepciones tipadas de `exceptions.py` y se convierten en errores de protocolo.

### Independencia del transporte

`McpManager.web()` y `local()` compilan mediante un único registro. HTTP registra una ruta API POST nativa y fija; STDIO solo se inicia para un identificador local registrado. Ambos caminos usan el mismo dispatcher, invocador, configuración y bus de eventos.

### Las indicaciones no son políticas

`ToolAnnotations`, `ContentAnnotations` y `CacheHint` comunican comportamiento a los clientes. No autorizan llamadas, no almacenan resultados en el servidor ni sustituyen validaciones. Use autenticación, hooks `authorize()` y servicios de aplicación para hacer cumplir políticas.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `server/primitives.py` | Bases declarativas `Tool`, `Resource`, `Prompt` y `Server`. |
| `server/compiler.py` | Nombres, esquemas, metadatos, manejadores, plantillas y capacidades al iniciar. |
| `server/catalog.py` | Catálogos buscables y acotados expuestos como herramientas sintéticas. |
| `dispatcher.py` / `invoker.py` | Despacho JSON-RPC, validación, resolución DI e invocación. |
| `responses.py` / `context.py` | Composición inmutable de respuestas e instantáneas de solicitud. |
| `transport/http.py` / `transport/stdio.py` | Adaptadores HTTP nativo y de flujos estándar. |
| `subscriptions/` | Publicación, listeners y suscripciones de recursos con ámbito. |
| `protocol/` | Estructuras wire, constantes, resultados, errores y validación de metadatos. |
| `manager.py` / `provider.py` | Registro, rutas, ciclo de vida y enlace de la fachada. |
| `state.py` | Estado de continuación firmado y ligado a una solicitud. |

## API pública

La raíz del paquete exporta `MCP_PROTOCOL_VERSION`, `McpConfig`, `McpRequest`, `McpContext`, `McpResponse`, `McpState`, `Tool`, `Resource`, `Prompt`, `Server`, `ToolCatalog`, `McpExtension`, `CacheHint`, `Icon`, `ToolAnnotations`, `ContentAnnotations`, `PromptArgument`, `Completion` e `InputRequiredResult`.

### Declaraciones primitivas

- `Tool[InputType, OutputType]` declara contratos de entrada/salida y un método `handle()`. Los hooks opcionales `available()` y `authorize()` se compilan cuando existen.
- `Resource` declara exactamente un `uri` absoluto o `uri_template` RFC 6570; el manejador de plantilla recibe variables decodificadas.
- `Prompt` declara argumentos string y devuelve mensajes; un `complete()` opcional proporciona sugerencias.
- `Server` agrupa primitivas, extensiones, caché, identidad, cambios de listas y suscripciones de recursos.
- `ToolCatalog(*tools, search_name=..., execute_name=...)` oculta un grupo grande tras herramientas acotadas de búsqueda y ejecución.

### Constructores de respuesta

`McpResponse.text()`, `image()`, `audio()`, `resource()`, `resourceLink()`, `structured()`, `error()` y `progress()` crean valores inmutables. `asAssistant()` y `asUser()` fijan roles; `withMeta()`, `withContentMeta()` y `withAnnotations()` devuelven copias modificadas tras validar.

### Manager y fachada

`McpManager` ofrece `web`, `local`, `getWebServer`, `getLocalServer`, `servers`, `dispatchHttp`, `startLocal`, notificaciones de cambio y `shutdown`. El código de aplicación normalmente accede al mismo singleton mediante `orionis.support.facades.Mcp`.

## Flujos de trabajo comunes

### Registrar endpoints web y locales

Declare servidores bajo `app/mcp/servers` y regístrelos durante el inicio. `web()` acepta una ruta fija sin parámetros, query ni fragmento. `local()` acepta un identificador estable con letras, dígitos, puntos, guiones bajos o guiones.

### Modelar una herramienta tipada

Use una entrada `Schema` cuando necesite validación y JSON Schema. Además del payload/contexto, las dependencias del manejador pueden inyectarse por tipo. Declare un tipo de salida para que Orionis valide el valor devuelto antes de serializarlo.

### Publicar cambios de catálogo

Active la capacidad correspondiente del servidor y llame `toolsChanged`, `promptsChanged`, `resourcesChanged` o `resourceUpdated`. Las notificaciones exigen que la clase de servidor esté registrada en este manager y se limitan a sus listeners.

### Probar el contrato wire

Use `orionis.test.McpTestClient` o `TestCase.mcp(...)`. El cliente usa el contenedor proporcionado, abre ámbitos reales, pasa bytes por el dispatcher y devuelve resultados decodificados junto con notificaciones.

## Ejemplos

### Declarar recursos y prompts

```python
from orionis.mcp import McpResponse, Prompt, PromptArgument, Resource, Server
from orionis.mcp.server.compiler import compile_server


class UserResource(Resource):
    uri_template = "demo://users/{user_id}"
    mime_type = "application/json"

    def handle(self, user_id: str) -> McpResponse:
        return McpResponse.structured({"id": user_id})


class ExplainPrompt(Prompt):
    arguments = (PromptArgument(name="topic", required=True),)

    def handle(self, topic: str) -> McpResponse:
        return McpResponse.text(f"Explain {topic}").asUser()


class ContentServer(Server):
    name = "Content"
    resources = (UserResource,)
    prompts = (ExplainPrompt,)


compiled = compile_server(ContentServer)
assert len(compiled.templates) == 1
assert "explain" in compiled.prompts
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Componer contenido de protocolo

```python
from orionis.mcp import ContentAnnotations, McpResponse

response = (
    McpResponse.structured({"status": "ok", "count": 2})
    .withMeta({"trace": "example"})
    .withContentMeta({"source": "docs"})
    .withAnnotations(ContentAnnotations(audience=("assistant",), priority=0.8))
)

assert response.structured_content == {"status": "ok", "count": 2}
assert response.meta["trace"] == "example"
assert response.content[0].meta["source"] == "docs"
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Inspeccionar una solicitud inmutable

```python
from orionis.mcp import McpRequest

request = McpRequest(
    id=7,
    method="tools/call",
    arguments={"query": ["orionis"]},
    meta={"io.modelcontextprotocol/clientCapabilities": {"sampling": {}}},
)

assert request.transport == "test"
assert request.arguments["query"] == ("orionis",)
assert "sampling" in request.client_capabilities
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Agrupar un conjunto grande de herramientas

```python
from orionis.mcp import Server, Tool, ToolCatalog
from orionis.mcp.server.compiler import compile_server


class PingTool(Tool):
    description = "Return a health marker."

    def handle(self) -> str:
        return "pong"


class CatalogServer(Server):
    name = "Catalog"
    tools = (ToolCatalog(PingTool),)


compiled = compile_server(CatalogServer)
assert set(compiled.tools) == {"search_tools", "execute_tools"}
assert "ping" in compiled.catalog_tools
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Registrar mediante la fachada

```python
from orionis.mcp import Server
from orionis.support.facades import Mcp


class ApplicationServer(Server):
    name = "Application"


Mcp.web("/mcp/application", ApplicationServer)
Mcp.local("application", ApplicationServer)
```

Validación: **Importación y sintaxis validadas** en CPython 3.14.6; el registro requiere una aplicación iniciada y la fachada enlazada.

### Verificar metadatos de respuesta

```python
from orionis.mcp import CacheHint, Icon, MCP_PROTOCOL_VERSION

hint = CacheHint(ttl_ms=30_000, scope="private")
icon = Icon(src="https://example.test/icon.png", mime_type="image/png")

assert MCP_PROTOCOL_VERSION == "2026-07-28"
assert hint.ttl_ms == 30_000
assert icon.src.startswith("https://")
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

## Configuración

| Variable de entorno | Predeterminado | Propósito |
|---|---:|---|
| `MCP_MAX_REQUEST_SIZE` | `HTTP_MAX_BODY_SIZE` o 1 MiB | Máximo de bytes por solicitud. |
| `MCP_DEFAULT_PAGE_SIZE` / `MCP_MAX_PAGE_SIZE` | 50 / 100 | Límites de paginación. |
| `MCP_MAX_CONCURRENT_REQUESTS` | `HTTP_MAX_CONCURRENT_REQUESTS` o 32 | Presupuesto concurrente por transporte. |
| `MCP_SUBSCRIPTION_BUFFER_SIZE` | 64 | Eventos almacenados por suscripción. |
| `MCP_MAX_SUBSCRIPTIONS` | 1024 | Presupuesto total de suscripciones. |
| `MCP_MAX_RESOURCE_SUBSCRIPTIONS` | 64 | Suscripciones de recursos por contexto. |
| `MCP_SUBSCRIPTION_KEEPALIVE` | 15.0 segundos | Intervalo de keepalive para streaming. |
| `MCP_ALLOWED_ORIGINS` | vacío | Orígenes HTTP explícitos de navegador. |
| `MCP_TOOL_SEARCH_MAX_RESULTS` | 20 | Máximo de resultados de catálogo. |
| `MCP_TOOL_SEARCH_MAX_CALLS` | 5 | Llamadas en una ejecución de catálogo. |
| `MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES` | 256 KiB | Máximo de salida de ejecución del catálogo. |
| `MCP_MAX_RESPONSE_SIZE` | 4 MiB | Máximo de respuesta serializada. |
| `MCP_MAX_METADATA_SIZE` | 64 KiB | Máximo de metadatos. |

Todos los presupuestos numéricos deben ser positivos; la página predeterminada no puede superar el máximo. Un `Origin` HTTP ausente se admite, pero uno presente debe coincidir exactamente con la lista HTTP(S) validada: no hay comodín ni excepción implícita de mismo origen.

## Integración con Orionis

`McpProvider` enlaza manager, configuración y bus de eventos en memoria, y fija la fachada `Mcp`. El router nativo marca los endpoints HTTP como rutas API. La autenticación se expone mediante cada `McpRequest` y las dependencias de manejadores usan ámbitos normales del contenedor.

La consola ofrece `reactor mcp:list`, `reactor mcp:start <name>` y generadores para servidores, herramientas, recursos y prompts. Solo se pueden iniciar nombres locales configurados; no se aceptan imports dinámicos arbitrarios.

## Errores y casos límite

- Los nombres deben cumplir `[A-Za-z0-9_.-]{1,128}`; los nombres inferidos se convierten a kebab-case.
- Las URI de recursos deben ser absolutas. Plantillas RFC 6570 complejas requieren un inverso `match(uri)` síncrono y estático/de clase.
- Los metadatos de aplicación y hooks de extensiones no pueden agregar claves reservadas del protocolo.
- Los iconos solo aceptan URI HTTPS o `data:`; la prioridad de contenido va de 0 a 1.
- Los valores de progreso deben ser finitos. El progreso se suprime sin el token de opt-in del cliente.
- La salida se valida antes de serializar; un valor incompatible con el tipo declarado produce un fallo de protocolo.
- Las instantáneas de solicitud son inmutables, pero los servicios inyectados pueden tener sus propias reglas de ciclo de vida y concurrencia.

## Rendimiento y concurrencia

La compilación mueve la reflexión, construcción de esquemas, metadatos de rutas y plantillas URI al inicio. Las definiciones compiladas son inmutables y se reutilizan entre solicitudes y transportes. Cada solicitud obtiene un ámbito de aplicación y resolución independiente de manejadores.

Concurrencia, bytes de solicitud/respuesta/metadatos, paginación, llamadas de catálogo y buffers de suscripción están acotados por `McpConfig`. Clientes lentos pueden agotar su buffer; los consumidores deben drenar eventos y cerrar siempre los streams. El bus en memoria es local al proceso y se cierra con el manager.

## Compatibilidad

- Versión de protocolo: `2026-07-28`; `SUPPORTED_VERSIONS` contiene actualmente solo esa versión.
- Python: 3.14+ porque la declaración pública de herramientas usa sintaxis genérica PEP 695.
- Clientes HTTP deben enviar encabezados JSON-RPC/MCP compatibles y tipos JSON o SSE aceptados por el transporte.
- STDIO reserva la salida estándar para frames del protocolo; los diagnósticos pertenecen a stderr.

## Notas de verificación

- `tests/mcp`: **140 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Se compilaron siete programas de documentación; seis programas autónomos se ejecutaron correctamente.
- El programa de registro por fachada se validó por importación/sintaxis porque requiere una aplicación iniciada.
- La documentación se contrastó con exports públicos, compilador, dispatcher, transportes, manager, configuración, validadores de metadatos, comandos de consola y cliente de pruebas MCP.

