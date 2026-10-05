# MCP nativo para Orionis

[English](README.md)

Orionis implementa **MCP 2026-07-28** mediante Streamable HTTP y STDIO. Cada servidor
utiliza el contenedor, los esquemas, la autenticación, el enrutador, el reporte de
excepciones y el ciclo de vida de la aplicación. HTTP funciona con los adaptadores
nativos ASGI y RSGI. No se crea otra aplicación ni se añade un runtime MCP externo.

Esta revisión no mantiene sesiones: cada solicitud incluye su versión de
protocolo y las capacidades del cliente. `server/discover` es opcional y no crea
una sesión. No se admiten `initialize`, `notifications/initialized`, `ping`, IDs de
sesión antiguos, endpoints SSE separados ni cambios implícitos a otras versiones.

## Declarar y registrar un servidor

```python
# app/mcp/servers/weather_server.py
from orionis.mcp import McpResponse, Server, Tool, ToolAnnotations
from orionis.schemas import Schema
from orionis.schemas.constraints import MinLength
from orionis.schemas.fields import Field


class WeatherInput(Schema):
    location: Field[str, MinLength(2)]


class WeatherTool(Tool[WeatherInput]):
    name = "weather"
    description = "Devuelve el pronóstico de una ciudad."
    annotations = ToolAnnotations(read_only=True, destructive=False)

    async def handle(self, payload: WeatherInput) -> McpResponse:
        return McpResponse.text(f"Pronóstico para {payload.location}")


class WeatherServer(Server):
    name = "Weather"
    version = "1.0.0"
    tools = (WeatherTool,)
```

```python
# routes/ai.py
from app.mcp.servers.weather_server import WeatherServer
from orionis.support.facades.mcp import Mcp

Mcp.web("/mcp/weather", WeatherServer)
Mcp.local("weather", WeatherServer)
```

Configura `app.withRouting(ai="routes/ai.py")` antes de `app.create()`. Estos archivos
se cargan durante el arranque de proveedores para HTTP y CLI, incluso cuando se
restauran rutas HTTP desde caché. `Mcp.web` devuelve el `FluentRoute` nativo: admite
los grupos de rutas y `.middleware(...)` habituales. Utiliza rutas estáticas y la
cadena API. Los nombres locales seleccionan clases registradas explícitamente;
nunca importan módulos indicados por el cliente.

```text
python reactor mcp:list
python reactor mcp:start weather
python reactor make:mcp-server Weather
python reactor make:mcp-tool Weather
python reactor make:mcp-resource Status
python reactor make:mcp-prompt Explain
```

## Entrada tipada, inyección y acceso

`Tool[Input, Output]` declara un `Schema` de Orionis u otra entrada tipada admitida,
y opcionalmente el esquema de salida estructurada. También existen los atributos
de clase `input` y `output`. Se conservan las restricciones nativas, descripciones
y metadatos JSON Schema. Las firmas y los esquemas se compilan al arrancar: las
declaraciones inválidas, los nombres duplicados y las anotaciones de cabeceras
incorrectas fallan antes de aceptar solicitudes.

Solo el parámetro declarado como payload recibe los argumentos de la herramienta.
Los constructores y los demás parámetros tipados se resuelven mediante el
contenedor existente. Las claves del cliente nunca se convierten en argumentos
arbitrarios para DI. Mantén disponibles en ejecución los tipos de servicios
inyectados para que Orionis pueda resolver sus anotaciones.

Inyecta `McpRequest`, también exportado como `McpContext`, para acceder a los datos
inmutables de la solicitud: `arguments`, `params`, `meta`, `uri_variables`,
`input_responses`, `request_state` y el contexto nativo de autenticación.
`identity` procede de la autenticación de Orionis, nunca de metadatos del cliente.
`native_request` solo está disponible en HTTP. STDIO no inventa un usuario HTTP.

Los hooks opcionales `shouldRegister(...)` y `authorize(...)` utilizan planes DI
compilados y se evalúan en cada solicitud. Se aplican a los listados, llamadas
directas, completado y catálogos. Pueden consultar la identidad o servicios
actuales. Las anotaciones de herramientas y `shouldRegister` no sustituyen la
autorización.

El scope HTTP nativo permanece vivo mientras se transmite la respuesta. STDIO
abre un scope independiente por invocación concurrente. Las instancias se
resuelven por operación; los registros compartidos no retienen solicitudes,
identidades, payloads ni servicios de scope. Los generadores mantienen su scope
hasta finalizar o cancelarse. Los handlers síncronos cortos ejecutan en el bucle
de eventos; utiliza servicios asíncronos para operaciones de E/S.

## Recursos, prompts y respuestas

Declara `Resource.uri` para una URI literal o `Resource.uri_template` para una
plantilla RFC 6570. Sus variables están en `request.uri_variables`. Una URI de
recurso nunca concede acceso al sistema de archivos. `Prompt.arguments` contiene
una tupla de `PromptArgument`; los argumentos de prompts son cadenas. Un prompt o
una plantilla puede implementar `complete(...)` y devolver `Completion` o una
lista de cadenas. Solo se anuncia completado cuando existe un proveedor real.

`McpResponse` ofrece `text`, `image`, `audio`, `resource`, `resourceLink`,
`structured`, `error` y `progress`. Imágenes y audio reciben bytes y un tipo MIME.
`structured` acepta cualquier valor JSON, incluidos arrays, escalares y `null`;
se valida el esquema de salida declarado. `asUser()` y `asAssistant()` asignan
roles de prompt. `withMeta`, `withContentMeta` y `withAnnotations` añaden metadatos
y anotaciones sin permitir sobrescribir campos reservados del protocolo.

Devuelve una respuesta, una secuencia de respuestas de contenido o un generador.
`McpResponse.progress(...)` solo produce notificaciones cuando la solicitud incluye
`progressToken`. El contenido se acumula dentro del límite configurado y termina
en un resultado final. HTTP usa SSE nativo para generadores y suscripciones, y JSON
normal para llamadas completas. El transporte controla cuándo lee el siguiente
elemento. Cerrar una fuente, incluso antes de iniciarla, libera su generador y su
cupo antes de destruir el scope.

Utiliza `McpResponse.error("mensaje seguro")` para un fallo de herramienta. Sus
fallos internos o de validación producen `isError`; las solicitudes de protocolo
inválidas producen errores JSON-RPC. Las excepciones inesperadas utilizan el
reporte nativo y mensajes públicos seguros. Los fallos HTTP de autenticación,
middleware o depuración no convierten el endpoint MCP en HTML ni en una
redirección al login. Se conservan las cabeceras de autenticación, reintento y
seguridad.

## Streamable HTTP

Envía una solicitud JSON-RPC por POST e incluye ambos tipos de respuesta:

```http
POST /mcp/weather HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: weather

{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"weather","arguments":{"location":"Bogotá"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}
```

`Mcp-Method` debe coincidir con `method`. `Mcp-Name` coincide con `params.name` en
herramientas y prompts, o con `params.uri` en lecturas de recursos. Los nombres de
cabecera no distinguen mayúsculas; se rechazan campos obligatorios duplicados.
Una cabecera reflejada ausente, malformada o diferente produce HTTP 400 / `-32020`.
Cuando la cabecera de versión está presente, los metadatos obligatorios ausentes
en el cuerpo producen `-32602`. Una versión coincidente pero no admitida produce
HTTP 400 / `-32022`; un método desconocido con metadatos válidos produce HTTP 404 /
`-32601`. Las notificaciones reciben HTTP 202 vacío. GET y DELETE reciben 405; se
conserva el tratamiento nativo de OPTIONS.

Todo `Origin` presente debe coincidir exactamente con `McpConfig.allowed_origins`,
también en métodos no admitidos y preflight. Se acepta la ausencia de Origin; la
lista vacía predeterminada rechaza todos los orígenes presentes. Configura orígenes
HTTP(S) explícitos con
`app.withConfigMcp(allowed_origins=("https://client.example",))`. Configura por
separado autenticación y CORS: permitir un origen no autentica al cliente. Para
desarrollo local, escucha en loopback.

Los endpoints MCP habilitan **por defecto** el monitoreo nativo de desconexión
ASGI/RSGI, incluidos los handlers que devolverán JSON normal. Reutilizan los
observadores de Orionis aunque `http.monitor_disconnects` global sea falso. La
desconexión cancela el handler o stream; su limpieza se protege de la cancelación
mientras se cierran productores y servicios. Las otras rutas mantienen su
configuración habitual.

### Parámetros reflejados en cabeceras

```python
from orionis.schemas.metadata import ExtraJsonSchema


class TenantInput(Schema):
    tenant: Field[str, ExtraJsonSchema({"x-mcp-header": "Tenant"})]
```

Una llamada HTTP con `arguments.tenant="north"` debe incluir
`Mcp-Param-Tenant: north`. Solo se admiten anotaciones en cadenas `properties`
estáticamente accesibles y tipos `string`, `integer` o `boolean`. Sus nombres
deben ser tokens HTTP válidos y únicos sin distinguir mayúsculas. No se admiten
reflejos dentro de arrays, rutas de esquemas condicionales o compuestos ni
referencias sin resolver. Un valor ausente o nulo exige omitir la cabecera.
Los enteros deben estar en el rango seguro JSON; su comparación es numérica.
Los booleanos usan `true` o `false`.

ASCII visible sin espacios en los extremos puede enviarse literalmente. Los
valores con caracteres no ASCII, de control o espacios externos utilizan
`=?base64?{BASE64_DE_UTF8}?=`. Un valor literal que ya tenga esa forma también debe
codificarse. Se rechazan Base64 y UTF-8 inválidos. Estas reglas también se aplican
al campo de nombre codificado. Las cabeceras se validan antes de ejecutar la
herramienta; el cuerpo sigue siendo la fuente de entrada y siempre se ejecutan
la validación y autorización ordinarias.

## STDIO

`mcp:start NOMBRE` lee JSON UTF-8 delimitado por saltos de línea y limitado en tamaño.
Escribe tramas JSON-RPC completas seguidas de un salto de línea. El punto de
entrada reserva stdout para el protocolo antes del bootstrap, proveedores y
análisis del comando; los diagnósticos usan stderr. Utiliza stderr para logs y no
escribas directamente en el descriptor de stdout.

Las solicitudes independientes ejecutan concurrentemente con scopes aislados y
un único escritor serializado. El lector permanece disponible para recibir
`notifications/cancelled` con `requestId`; solo se cancela esa invocación. Se
rechazan IDs activos duplicados y solicitudes que excedan la capacidad. EOF
cancela llamadas pendientes, espera la limpieza y termina. En Windows se utilizan
puentes limitados con hilos daemon para que una lectura de tubería bloqueada no
retenga el cierre del executor del bucle de eventos.

## Suscripciones y múltiples rondas explícitas

`subscriptions/listen` es una solicitud de larga duración con un filtro
`notifications`: `toolsListChanged`, `promptsListChanged`, `resourcesListChanged`
y/o `resourceSubscriptions`. Habilita `list_changed=True` y
`resource_subscriptions=True` en el servidor. La primera notificación es
`notifications/subscriptions/acknowledged` e indica el subconjunto aceptado.
Los recursos se comprueban mediante disponibilidad y autorización al admitir la
suscripción. Cada notificación lleva
`_meta["io.modelcontextprotocol/subscriptionId"]` con el ID original.

Publica mediante `await Mcp.toolsChanged(ClaseServidor)`, `promptsChanged`,
`resourcesChanged` o `resourceUpdated(ClaseServidor, uri)`. El `IMcpEventBus`
predeterminado es local al worker y solo retiene claves de servidor, filtros y un
número limitado de cambios. Los cambios duplicados se combinan; un suscriptor
sobrecargado finaliza ordenadamente. No distribuye eventos entre workers ni
mantiene historial de reconexión. Enlaza una implementación distribuida de
`IMcpEventBus` cuando tu aplicación lo requiera. Los latidos HTTP son comentarios
SSE. El cierre finaliza las suscripciones; las desconexiones HTTP y cancelaciones
STDIO eliminan los listeners.

Para pedir entrada adicional, devuelve
`InputRequiredResult(inputRequests={...}, requestState=...)`. Se admiten
elicitation, roots y sampling según esta revisión. Sampling se conserva por
compatibilidad con el protocolo, aunque upstream lo marca como obsoleto. Se
comprueban las capacidades de la solicitud actual. El cliente reintenta el método
original con `inputResponses` y el estado explícito. No se envían solicitudes
JSON-RPC del servidor al cliente ni se almacena una sesión oculta. La aplicación
debe validar el significado de la entrada devuelta antes de actuar.

Opcionalmente, `McpState.seal(request, value, ttl=300)` / `open(request)` utiliza
el encriptador AEAD nativo y requiere `AES-128-GCM` o `AES-256-GCM`. Vincula el
estado a caducidad, servidor, método, destino, argumentos e identidad autenticada.
Workers con la misma clave pueden validarlo. No impide por sí solo reutilizar un
token válido: implementa idempotencia persistente para los efectos secundarios.
El dispatcher proporciona el `server_id` confiable; la aplicación no debe inventar
ni reemplazar ese identificador al sellar estado.

## Catálogos y extensiones

`Server.tools = (ToolCatalog(FirstTool, SecondTool),)` publica los puntos limitados
`search_tools` y `execute_tools`. Las herramientas del catálogo no aparecen en el
listado ordinario. La búsqueda usa un índice léxico determinista precompilado y
comprueba acceso por solicitud. La ejecución reutiliza la validación de entrada,
acceso, salida y errores ordinarios; limita las llamadas y los bytes de salida.

Una única llamada anidada puede devolver MRTR. Si un lote de varias llamadas
requiere otra ronda, devuelve un error que indica invocar individualmente esa
herramienta: los efectos ya completados no se repiten automáticamente. El progreso
anidado se consume sin acumularlo y no se reenvía como progreso de otra solicitud.

Las cabeceras HTTP reflejan el esquema real de `execute_tools`. No pueden reflejar
campos dentro del array `calls`, por lo que las anotaciones de herramientas
internas no crean cabeceras externas adicionales. Expón una herramienta
directamente si un proxy o una política de seguridad necesita inspeccionar sus
argumentos reflejados. La autorización interna siempre se ejecuta.
Una llamada directa al nombre de una herramienta del catálogo valida sus propias
cabeceras reflejadas.

`McpExtension` declara capacidades, handlers de métodos, decodificadores
precompilados y un hook de esquema opcional. No se habilitan extensiones por
defecto; Tasks no está implementado. Los hooks de esquema pueden añadir campos
propios de la extensión, pero no cambiar metadatos estándar ni restricciones
nativas de validación. La aplicación define la semántica y la compatibilidad de
sus extensiones.

## Límites, arquitectura y pruebas

`app.withConfigMcp(...)` configura límites inmutables y validados:

| Parámetro | Predeterminado | Alcance |
| --- | ---: | --- |
| `max_request_size` | 1 MiB | Cuerpo HTTP / trama STDIO |
| `max_response_size` | 4 MiB | Respuesta codificada / contenido acumulado |
| `max_metadata_size` | 64 KiB | Metadatos de solicitud / resultado de aplicación |
| `max_concurrent_requests` | 32 | Cada endpoint HTTP o transporte STDIO, por worker |
| `default_page_size` / `max_page_size` | 50 / 100 | Configuración de paginación |
| `subscription_buffer_size` | 64 | Cambios distintos pendientes por listener |
| `max_subscriptions` | 1024 | Bus predeterminado, por worker |
| `max_resource_subscriptions` | 64 | Filtros de recursos por solicitud listen |
| `subscription_keepalive` | 15 s | Intervalo de comentario HTTP inactivo |
| `tool_search_max_results` | 20 | Resultados de búsqueda |
| `tool_search_max_calls` | 5 | Llamadas anidadas por ejecución |
| `tool_search_max_output_bytes` | 256 KiB | Salida de catálogo |

Los streams de larga duración ocupan un cupo hasta cerrarse. HTTP también respeta
los límites del kernel. La paginación usa cursores opacos sin sesión y vuelve a
comprobar el acceso en cada solicitud. Las indicaciones de caché predeterminadas
son `ttlMs=0` y `cacheScope="private"`. `CacheHint` indica caché al cliente; no crea
una caché de resultados en el servidor.

```text
Arranque → registro inmutable + esquemas + planes DI y de cabeceras
Router HTTP → middleware/scope nativo → transporte HTTP ┐
Lector STDIO → tareas limitadas + scope nativo nuevo    ├→ dispatcher → primitiva
TestCase.mcp → aplicación + scope nativo nuevo         ┘
Bytes / iterador propio → JSON/SSE nativo o escritor STDIO serializado
```

La política genérica de endpoint HTTP se resuelve una vez al arrancar. Su consulta
por ruta controla Origin y la presentación de errores alrededor del kernel
existente. El kernel no importa MCP ni usa un segundo router. La caché de rutas
continúa apuntando al controlador MCP nativo y estable.

```python
from orionis.test import TestCase

class TestWeather(TestCase):
    async def testWeather(self) -> None:
        """Verify the weather tool through the native test runner.

        Returns
        -------
        None
            Check the successful tool response and its text.
        """
        client = await self.mcp(WeatherServer)
        response = await client.tool("weather", {"location": "Bogotá"})
        response.assertOk()
        response.assertTextContains("Bogotá")
```

Utiliza `client.stream(...)` para suscripciones y cancelaciones; `request(...)`
recoge intercambios finitos. El helper usa la aplicación que `reactor test` ya
arrancó; `app=` permite un contenedor aislado y `config=` fija límites explícitos.
Cierra los streams al terminar antes de agotar el iterador, por ejemplo con
`contextlib.aclosing`. El cliente prueba bytes mediante el dispatcher nativo.
Adaptadores HTTP, rutas, cabeceras, Origin y middleware tienen tests independientes.

```text
python reactor test --start-dir=tests/mcp --verbosity=1
python reactor test --start-dir=tests/test --verbosity=1
python reactor test --start-dir=tests/http --verbosity=0
```

Las comprobaciones externas de conformidad e Inspector requieren herramientas
y fixtures propias. La carpeta de pruebas contiene módulos nativos de Orionis;
no incluye esos ejecutores, snapshots de esquemas ni informes generados.

Las decisiones siguen la [especificación oficial fechada](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/75db1e987cbbba6d170315dc99d0dfc440754aef/docs/specification/2026-07-28)
y su [esquema fechado](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/75db1e987cbbba6d170315dc99d0dfc440754aef/schema/2026-07-28).
