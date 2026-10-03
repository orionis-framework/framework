# Server-Sent Events (SSE)

SSE transmite una secuencia de eventos de texto UTF-8 en una respuesta HTTP.
Orionis exporta `ServerSentEvent` y `EventStreamResponse` desde `orionis.http`,
con `response.eventStream(...)` como entrada de la factoría. La API es idéntica
bajo ASGI y Granian RSGI y utiliza las rutas, middleware y scope HTTP existentes.

```python
from collections.abc import AsyncIterator
from orionis.http import EventStreamResponse, ServerSentEvent, response


async def notifications() -> AsyncIterator[ServerSentEvent]:
    """Yield the connection marker and an application message.

    Yields
    ------
    ServerSentEvent
        Named events with application-owned cursors.
    """
    yield ServerSentEvent(
        event="connected",
        data="ready",
        id="1",
    )

    yield ServerSentEvent(
        event="message",
        data="Hello",
        id="2",
    )


async def handler() -> EventStreamResponse:
    """Return an event response without consuming its producer.

    Returns
    -------
    EventStreamResponse
        Lazy response consumed by the HTTP adapter.
    """
    return response.eventStream(notifications())
```

Registra `handler` con la API habitual `Route.get(...)`. También puedes retornar
`EventStreamResponse(notifications())` directamente. Construir la respuesta es
síncrono; el adaptador HTTP consume la fuente durante la entrega.

## API pública y formato

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ServerSentEvent:
    data: str | None = None
    event: str | None = None
    id: str | None = None
    retry: int | None = None
    comment: str | None = None

    def encode(self) -> bytes: ...
```

Todos los campos son argumentos opcionales por nombre. Los eventos son
inmutables. `encode()` devuelve bytes UTF-8 y emite los campos en este orden:
comment, event, id, retry, data. Cada bloque termina con `\n\n`, incluido un
evento sin campos. Los campos ausentes (`None`) se omiten; las cadenas vacías se
conservan como valores vacíos. Un evento sin campos es un bloque vacío que no
despacha un mensaje al cliente SSE.

La interpretación del cliente sigue el
[estándar de eventos SSE](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation).

| Campo | Significado y validación |
|---|---|
| `data` | Texto del mensaje. Cada línea produce una línea `data: `. |
| `event` | Nombre del evento. Rechaza CR y LF. |
| `id` | Identificador del evento de la aplicación. Rechaza CR, LF y NUL. Un valor vacío reinicia el ID del cliente. |
| `retry` | Entero no negativo que sugiere al cliente el retraso de reconexión en milisegundos. Rechaza booleanos. |
| `comment` | Texto del comentario. Cada línea produce una línea `: `; los comentarios no despachan mensajes. |

Los campos de texto solo aceptan `str` o `None`; los tipos incorrectos producen
`TypeError` al construir el evento. Los caracteres inválidos de `event`/`id` y
un `retry` negativo producen `ValueError`. Los datos y comentarios normalizan
CRLF y CR a LF antes de separar líneas; conservan las líneas vacías finales.

```python
ServerSentEvent(data="first\r\nsecond\rthird").encode()
# b"data: first\ndata: second\ndata: third\n\n"

ServerSentEvent(event="message", id="42", data="hello").encode()
# b"event: message\nid: 42\ndata: hello\n\n"

ServerSentEvent(data="").encode()
# b"data: \n\n"
```

No existe serialización JSON implícita. Serializa explícitamente los datos
estructurados:

```python
import json

event = ServerSentEvent(data=json.dumps({"status": "ready"}))
```

`EventStreamResponse` hereda de `StreamingResponse` y acepta los siguientes
argumentos; `response.eventStream` acepta los mismos argumentos y devuelve un
`EventStreamResponse`:

```python
def __init__(
    self,
    content: AsyncIterable[ServerSentEvent | str] | Iterable[ServerSentEvent | str],
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None: ...
```

Un elemento `str` tiene el mismo formato que `ServerSentEvent(data=item)`, pero
se codifica directamente sin crear un evento temporal. Un elemento no
admitido, incluidos bytes sin procesar, produce `TypeError` durante la iteración.
Una fuente que no sea iterable asíncrono ni síncrono produce `TypeError` al
construir la respuesta. Los eventos se codifican individualmente como el
`AsyncIterable[bytes]` que consumen los adaptadores existentes. Pasa `["hello"]`
para un evento de texto: una cadena suelta es iterable y produce un evento por
carácter. `getBody()` es `None`. Usa productores asíncronos para E/S; los
iterables síncronos se ejecutan en el event loop y no deben bloquearlo.

## Headers y proxies

Los headers predeterminados son:

```http
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
X-Accel-Buffering: no
```

Se conservan los valores explícitos de estos headers y sus nombres se comparan
sin distinguir mayúsculas. Mantén un content type SSE válido para clientes SSE.
`Content-Length` se elimina aunque se proporcione y los adaptadores lo omiten
en la salida SSE si se añade después. Orionis no añade `Connection: keep-alive`;
la gestión de conexiones pertenece al servidor HTTP, también bajo HTTP/2.

`X-Accel-Buffering: no` es una indicación para proxies compatibles. Configura el
proxy inverso, balanceador y middleware de compresión reales para transmitir
datos incrementalmente y admitir la duración deseada de conexión. Un proxy
puede acumular datos o cerrar una conexión inactiva pese a estos headers.
Verifica la ruta completa de despliegue; un envío de transporte exitoso no
demuestra que el cliente final haya recibido el evento.

## Desconexión, cancelación y cierre

La respuesta es responsable del iterador adquirido durante la entrega. Ante
finalización normal, desconexión, error de productor/transporte o cancelación
de la petición, el cleanup cierra ese iterador esperando `aclose()` si existe,
o mediante `close()` para un iterador síncrono. Una respuesta sin iniciar cierra
la propia fuente si expone un método de cierre, sin iniciar su iteración.
Esto incluye fallos de serialización y codificación de headers antes de que el
transporte empiece a enviar, tanto para GET como para HEAD.
Coloca la liberación de recursos de la aplicación en el bloque `finally` del
productor. Una vez iniciado, el iterador se cierra sin exigir otro evento.

ASGI observa `receive()` en paralelo con la entrega para detectar
`http.disconnect`. Una desconexión cancela la operación de streaming, incluido
un productor que espera su próximo evento. Mientras espera, el watcher consume
y descarta los mensajes `http.request` pendientes. Lee cualquier cuerpo de
petición necesario en el handler antes de retornar la respuesta; no consumas
`request.body()` o `request.stream()` desde el productor en paralelo con el
watcher.

RSGI usa `protocol.response_stream(...)` y espera `transport.send_bytes(...)`.
Observa en paralelo el awaitable soportado `protocol.client_disconnect()`, de
modo que también puede cancelar un productor silencioso al desconectar. El
transporte HTTP de Granian no tiene un método público `close()`; Orionis cierra
el iterador fuente y devuelve el control al protocolo. Al terminar la entrega
cancela y espera el watcher porque una conexión HTTP keep-alive puede sobrevivir
a una respuesta. La [especificación RSGI de Granian 2.8.4](https://github.com/emmett-framework/granian/blob/v2.8.4/docs/spec/RSGI.md#http-protocol-interface)
documenta ese contrato.

Ambos adaptadores detienen y esperan sus tareas temporales antes de retornar.
Una desconexión normal del cliente constituye una entrega incompleta. Los
errores del productor, transporte y cierre se propagan; la cancelación de la
petición conserva `CancelledError` cuando el cierre termina correctamente. Un
fallo del cierre tiene prioridad y conserva la cancelación como causa. Los
errores simultáneos de entrega y watcher se conservan en un grupo de excepciones.
El orden de finalización se registra mediante callbacks: si ambas operaciones
terminan en el mismo turno del event loop, una desconexión anterior sigue
omitiendo las tareas de fondo, y una entrega exitosa anterior conserva el éxito.
Los productores deben cooperar con la
cancelación: bloquear con trabajo síncrono o suprimir `CancelledError` impide
un cierre oportuno.

El framework protege y espera su cierre asíncrono explícito del iterador.
Si la cancelación puede llegar mientras el productor ya espera la liberación
de sus recursos, protege y espera también esa operación crítica. Cancelar un
productor no puede reiniciar cleanup abandonado dentro de su bloque `finally`.

`HEAD` envía headers y un cuerpo final vacío sin iniciar ni consumir el productor
SSE. Una `StreamingResponse` ordinaria no obtiene vigilancia de desconexión SSE
por establecer `Content-Type: text/event-stream`.

## Scope de petición y tareas de fondo

`KernelHTTP` espera la entrega dentro del scope de aplicación de la petición.
Las dependencias scoped siguen disponibles durante el streaming y el cleanup;
SSE no abre un scope adicional. Los recursos de la petición se liberan tras la
entrega y las tareas de fondo exitosas, también en rutas de error y cancelación.

La tarea de fondo de una respuesta se ejecuta únicamente tras agotar normalmente
el productor y completar correctamente la entrega y el cierre. Una desconexión
anticipada, error de productor, transporte o cierre, o cancelación omite las
tareas de fondo. Usa el `finally` del productor para liberar recursos necesarios:
una tarea de fondo no es un callback de desconexión ni de cleanup. `HEAD`
conserva el comportamiento de tareas de fondo de una respuesta exitosa sin
consumir la fuente.

## Heartbeat manual y reconexión

Emite un comentario cuando la aplicación necesite un heartbeat:

```python
yield ServerSentEvent(comment="ping")
# b": ping\n\n"
```

Orionis no crea timers, schedulers ni tareas periódicas de heartbeat. La
aplicación decide cuándo emitir comentarios. Pueden mantener actividad visible
para los proxies sin entregar un evento de mensaje, pero siguen aplicándose
los límites de inactividad del despliegue.

Consulta el cursor de reconexión mediante la API normal de headers:

```python
from orionis.http import Request


def last_event_id(request: Request) -> str | None:
    """Read the reconnect cursor without interpreting its application meaning.

    Parameters
    ----------
    request : Request
        Current HTTP request.

    Returns
    -------
    str | None
        Client-provided cursor, or None when the header is absent.
    """
    return request.headers.get("Last-Event-ID")
```

`id` establece el cursor de evento ofrecido al cliente; al reconectar, este puede
devolverlo en `Last-Event-ID`. Valida e interpreta ese header en la aplicación.
`retry` sugiere al cliente un retraso de reconexión. Orionis no reconecta desde
el servidor, almacena sesiones ni historial, persiste cursores o reproduce
eventos perdidos. Una nueva petición HTTP obtiene su propio scope habitual.

## Rendimiento y concurrencia

La entrega sigue `producir un evento → codificar UTF-8 → esperar envío del
transporte → pedir siguiente evento`. El envío esperado aporta backpressure.
Orionis no añade colas de eventos, copias completas del stream, workers en hilos,
polling, sleeps internos ni estado global de conexión. La memoria depende del
evento actual y del estado del productor, no del número de eventos ya enviados;
esta garantía no incluye los buffers de transporte y proxies.

Cada petición SSE abierta retiene su scope y ocupa capacidad del límite HTTP
de peticiones concurrentes hasta terminar. Planifica capacidad para conexiones
prolongadas y mantén pequeñas las dependencias por petición. Usa E/S asíncrona
que coopere con la cancelación y libera suscripciones y recursos en `finally`.
Broadcasting, pub/sub, almacenamiento de eventos y políticas de autenticación
son responsabilidades de la aplicación.

## Inicialización e inyección de dependencias

| Componente | Trabajo inmediato | Trabajo diferido |
|---|---|---|
| Inicializador del paquete HTTP | Declarar la tabla de exportaciones públicas. | Resolver y cachear las exportaciones en el primer acceso. |
| `ServerSentEvent` | Validar una vez tipos, metadatos y retry de sus campos inmutables. | Codificar bytes al llamar a `encode()`; no cachear payloads arbitrarios. |
| `EventStreamResponse` | Validar metadatos de respuesta, retener la fuente y establecer headers. | No invocar el iterador fuente, realizar E/S ni crear tareas en `__init__`. |
| `_EventStreamIterator` | Clasificar el protocolo de la fuente e inicializar estado vacío. | Adquirir el iterador al pedir el primer evento; crear trabajo de limpieza solo al cerrar. |
| Factoría y adaptadores de respuesta | Construir objetos sin estado durante el import o arranque. | Estos objetos no requieren resolución diferida de servicios. |
| Controlador HTTP | Precargar la clase y sus planes de dependencias durante el arranque del kernel. | Construir el controlador y resolver los servicios de petición/scoped dentro de cada petición. |

Mantén la E/S bloqueante fuera de constructores y productores síncronos. Los
controladores siguen usando `Container.build()` y `Container.call()`; los
handlers de función usan `Container.invoke()`. SSE no introduce un proveedor,
un contenedor independiente, reflexión por evento ni una ruta nueva para
construir modelos, mailers o jobs. No se deben cachear globalmente objetos
scoped. Los manuales del [contenedor](../../container/docs/README.md) y de
[introspección](../../introspection/docs/README.md) describen esos contratos.

## Hallazgos de la revisión

La revisión cubrió los 12 archivos Python pendientes y los cuatro manuales
HTTP/SSE. No se confirmó un defecto crítico dentro de este alcance; esto no
garantiza la seguridad de cualquier productor de aplicación o despliegue.

### Alto: propiedad de recursos antes del envío

La serialización de headers podía fallar antes de entrar al bloque de limpieza
del stream en ambos adaptadores. La fuente no recibía entonces un cierre
explícito. Ambos adaptadores esperan ahora su cierre en esa ruta de error,
incluidos HEAD y los fallos de codificación ASGI. Esto evita abandonar
suscripciones o handles; el CPU y la latencia adicionales de cierre aparecen
solo al fallar la preparación. El cierre aún puede esperar indefinidamente si
el finalizador de la aplicación no coopera. Dos métodos de regresión cubren
cinco escenarios que fallaban antes de la corrección.

### Alto: orden entre desconexión y finalización

El resultado anterior de `asyncio.wait(FIRST_COMPLETED)` podía contener ambas
tareas sin conservar cuál terminó primero. Esto permitía ejecutar tareas de
fondo tras una desconexión anterior. Un callback compartido registra la primera
finalización en un futuro; ambas tareas siguen esperándose y los errores
simultáneos permanecen visibles. La coordinación usa espacio constante y deja
de construir los conjuntos de resultado de `wait()`. El coste de mantenibilidad
es registrar y retirar explícitamente el callback, con pruebas de ambos órdenes.

### Medio: codificación y objetos temporales

Cada texto construía un dataclass congelado y validaba campos que no utilizaba.
La codificación directa elimina ese objeto y ese trabajo. Los datos y comentarios
estructurados prefijan ahora sus líneas con `str.replace`, sin listas de
`split()`, expresiones generadoras ni un string temporal por línea. El tiempo
sigue siendo lineal en los bytes del payload, pero la lista de composición
tiene como máximo cinco elementos en lugar de crecer con el número de líneas.
Los bytes de salida y las copias necesarias de normalización siguen siendo
proporcionales al tamaño del payload. Las dos rutas de formato requieren pruebas
de equivalencia; ninguna cachea mensajes ni cambia la API pública.

### Bajo: limpieza y preparación de respuesta

Un cierre asíncrono ya no necesita una lista de resultados de `gather()` con
un elemento. La espera compartida protege una notificación de finalización
exitosa y después lee el resultado de la tarea original. Esto evita también
que `shield` de Python 3.14 registre como no gestionado un fallo que su dueño
ya está manejando. Las cancelaciones repetidas siguen esperando el cierre y
relanzando la cancelación. El coste es un pequeño conjunto de helpers privados
de ciclo de vida; no añade trabajo de limpieza por evento.

Los serializadores de headers omiten la lista adicional de filtrado cuando no
existe `Content-Length`, ahorrando una lista y un recorrido de headers por
serialización. La serialización normal sigue siendo lineal en los headers;
una longitud explícita añadida después conserva la ruta de filtrado. Las listas
devueltas y los metadatos mantienen su mutabilidad actual. También se eliminó
una adquisición redundante del iterador SSE.

La validación y el despacho RSGI se separaron en helpers concretos para cumplir
los límites de complejidad del lint. No se añadieron exclusiones de reglas ni
comentarios de supresión. Los métodos implementados usan camelCase y las
funciones de módulo snake_case; los dunders de Python y los alias exigidos por
protocolos externos conservan sus nombres estándar.

## Mediciones y verificación

Se utilizó CPython 3.14.6 en Windows 11. La versión mínima sigue siendo Python
3.14. Las mediciones de codificación son medianas de siete rondas alternadas de
100.000 operaciones. La referencia conserva el codificador previo con
split/join; las mediciones de texto incluyen construir el `ServerSentEvent`
temporal, mientras las de eventos estructurados usan un evento ya construido
con `event="update"`, `id="42"` y `comment="ping"`. Se comprobó igualdad de bytes
antes de medir. Los payloads fueron `"ready"`, `"line\r\n" * 64` y
`"\u00e9\u4e16\u754c" * 32`.

| Caso de codificación | Antes (us) | Después (us) | Razón | Pico antes/después (bytes) |
|---|---:|---:|---:|---:|
| Texto corto | 1.319 | 0.165 | 7.97x | 1276 / 242 |
| Evento estructurado corto | 1.005 | 0.489 | 2.06x | 1024 / 586 |
| Texto con 64 separadores CRLF | 11.052 | 2.761 | 4.00x | 8808 / 2001 |
| Evento estructurado con 64 separadores CRLF | 11.044 | 3.709 | 2.98x | 8460 / 3044 |
| Texto Unicode | 2.474 | 0.651 | 3.80x | 1585 / 699 |
| Evento estructurado Unicode | 2.128 | 1.272 | 1.67x | 1417 / 1281 |

Los valores de memoria son picos transitorios de `tracemalloc` durante 1.000
operaciones, no memoria retenida, RSS ni bytes por conexión. Los métodos de
headers se midieron por separado con los mismos datos, despacho de método y
herencia: nueve rondas alternadas de 200.000 llamadas. ASGI pasó de 0.833 a
0.699 us (1.19x); RSGI pasó de 0.572 a 0.445 us (1.29x). Se descartó una
comparación entre función libre y método por no medir rutas equivalentes.

Comprobaciones realizadas:

- HTTP: 869/869; contenedor: 253/253; introspección: 1022/1022.
- SSE incluye 66 pruebas, siete añadidas en esta revisión, con 32 peticiones
    simultáneas a controladores por transporte y cierres/desconexiones mezclados.
- Auditoría AST: 84 definiciones de producción y 139 de tests con nombres,
    docstrings y anotaciones válidos, sin definiciones de método duplicadas.
- `python -m ruff check .` pasó; el análisis de SonarQube for IDE y los
    diagnósticos del editor quedaron limpios en los 12 archivos Python pendientes
    con la configuración existente.

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor test --start-dir=tests/http --verbosity=0
.\.venv\Scripts\python.exe reactor test --start-dir=tests/container --verbosity=0
.\.venv\Scripts\python.exe reactor test --start-dir=tests/introspection --verbosity=0
.\.venv\Scripts\python.exe -m ruff check .
```

Son comprobaciones locales de funcionamiento y microbenchmarks, no mediciones
de throughput o latencia HTTP contra Starlette. Esta revisión no certificó el
backpressure de red nativa, los proxies de despliegue, la saturación multiproceso
ni un Quality Gate remoto de SonarQube.
