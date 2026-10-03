# Hubs Realtime

Orionis Realtime agrega RPC explícito, tipado y bidireccional sobre la
[API WebSocket](../../http/docs/websockets.es.md). Los sockets raw siguen siendo
independientes de Hub. La capa opcional reutiliza Application, routing,
middleware, scopes y Container tanto con ASGI como con RSGI.

La especificación completa del cliente es
[Orionis Realtime Protocol v1](protocol-v1.md). No implementa SignalR y esta
versión no incluye un SDK JavaScript público.

## Primer Hub

```python
from orionis.realtime import Hub, remote
from orionis.support.facades import Route

class CalculatorHub(Hub):
    @remote
    async def add(self, a: int, b: int) -> int:
        return a + b

Route.hub("/hubs/calculator", CalculatorHub)
```

Después de recibir `ready`, el cliente envía
`{"type":"invoke","id":"1","target":"add","args":[2,3]}` y recibe
`{"type":"completion","id":"1","result":5}`. `None` se serializa como
`null`. Un error de argumentos o de ejecución completa esa invocación sin
cerrar necesariamente la conexión.

Sólo se exponen métodos `@remote`. Los helpers públicos no se publican de forma
automática. `@remote(name="sendMessage")` define un alias sin envolver el método.
Nombres privados, alias duplicados, métodos estáticos/de clase, parámetros
variádicos o exclusivamente posicionales y anotaciones no resolubles se rechazan
al registrar el Hub. Todos los parámetros requieren anotaciones explícitas y
sus tipos deben estar importados en runtime para poder inspeccionarse al arrancar.

Se admiten métodos async y métodos síncronos breves. Los métodos síncronos se
ejecutan en el event loop, sin crear threads; el I/O debe usar servicios async.
Los trabajos durables o extensos pertenecen a Queue.

## DI y scopes por invocación

```python
from app.services.orders import OrderService

class OrdersHub(Hub):
    def __init__(self, service: OrderService) -> None:
        self.service = service

    @remote
    async def find(self, order_id: int, service: OrderService) -> object:
        return await service.find(order_id)
```

El cliente sólo suministra `order_id`. `service` siempre se resuelve mediante
Container: un payload que intente reemplazarlo se rechaza. Las posiciones de
`args` omiten los servicios inyectados. Las clases de servicio concretas,
contratos, contexto del framework y dependencias opcionales permanecen bajo DI.
Incluso `service: OrderService | None = None` resuelve el servicio; ese default
no concede control al cliente.

Tipos primitivos, colecciones tipadas compatibles, enums y `msgspec.Struct` se
validan como datos. Las conversiones son estrictas y los schemas Orionis ejecutan
sus reglas existentes. Los defaults y schemas convertidos se pasan explícitamente
al método, sin reutilizar el body de una petición HTTP. Las uniones ambiguas entre
datos y servicios se rechazan durante el arranque.

El kernel conserva un scope durante toda la conexión. Cada RPC admitida abre
un scope independiente basado en `contextvars` y crea una instancia nueva de Hub.
Dos invocaciones concurrentes tienen servicios `SCOPED` diferentes. Constructor
y método dentro de la misma invocación comparten los servicios de ese scope.
Socket, contexto y selectores de conexión se vuelven a registrar explícitamente.

No guardes estado global o de conexión en una instancia de Hub. `HubContext` es
inmutable y contiene `connection_id`, `socket` y `user`. Una conexión no equivale
a un usuario ni a una sesión; un usuario puede mantener varias conexiones.

## Lifecycle, autenticación y autorización

```python
class ChatHub(Hub):
    async def onConnect(self) -> None:
        if self.context.user is None:
            await self.context.socket.reject(status_code=401)
            return
        await self.groups.join("authenticated")

    async def onDisconnect(self, code: int, reason: str | None = None) -> None:
        pass
```

La conexión está registrada provisionalmente durante `onConnect`, por lo que
puede incorporarse a grupos, pero sólo puede recibir envíos mediante selectores
después del mensaje `ready`. El runtime acepta el socket tras el hook si éste
no lo aceptó antes. No envíes mensajes del protocolo ni invoques clientes desde
`onConnect`: todavía no recibieron `ready`.

Toda salida cancela RPC activas, resuelve los futures pendientes con error,
elimina grupos y la entrada del registro, y ejecuta `onDisconnect`. Sus errores
no impiden liberar el socket. El hook de desconexión tiene un límite temporal;
el shutdown existente del kernel cancela los owners de conexión. El código de
aplicación debe cooperar con la cancelación.

Usa `Route.hub(...).middleware(TuWebSocketMiddleware)` con el contrato
`handle(socket: WebSocket, call_next: WebSocketNext) -> None`. No se admiten
middlewares HTTP que requieren Request/Response. El socket expone headers,
cookies, query, path, client/server y scheme del handshake.

WebSocket no ejecuta automáticamente middleware de sesión HTTP ni restauración
de identidad por sesión/token. El middleware de conexión debe validar sus
credenciales mediante los servicios de identidad/guards apropiados y publicar
el contexto Auth existente. Tras obtener `validated_user` e inyectar un
`IPermissionRepository` llamado `permissions`, puede hacer:

```python
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context

bind_auth_context(AuthenticationContext(
    identity=validated_user,
    guard="websocket",
    repository=permissions,
))
```

Los métodos remotos usan `await Auth.can(...)` o servicios de autorización
inyectados. No existe otra ACL dentro de Realtime. Estar autenticado no autoriza
todas las operaciones ni el acceso a cualquier grupo.

Cada invocación copia la identidad y restricciones de credencial del contexto
Auth integrado, con locks y snapshots de permisos independientes. Las
implementaciones personalizadas de `IAuthenticationContext` deben adaptarse
explícitamente al contexto integrado: esta versión no presupone un contrato de
clonación personalizado. La conexión no revalida automáticamente su credencial
original en cada llamada; la aplicación debe añadir las verificaciones de
revocación que requiera a su autorización.

## Grupos, broadcasts y selectores

```python
class ChatHub(Hub):
    @remote
    async def joinRoom(self, room: str) -> None:
        # Autorizar el acceso antes de incorporar esta conexión.
        await self.groups.join(room)

    @remote
    async def sendMessage(self, room: str, message: str) -> dict:
        result = await self.clients.group(room).send(
            "messageReceived", {"room": room, "message": message},
        )
        return {"sent": result.sent, "failed": result.failed}
```

`await self.groups.leave(name)` es idempotente. Repetir `join` no consume otro
slot. La desconexión elimina membresías y grupos vacíos. Los grupos pertenecen
al namespace del Hub: nombres iguales en Hubs diferentes no mezclan destinatarios.

| Selector | Destinatarios |
|---|---|
| `self.clients.all` | Conexiones listas de este Hub. |
| `self.clients.caller` | La conexión actual. |
| `self.clients.others` | Las otras conexiones listas de este Hub. |
| `self.clients.client(id)` | Una conexión explícita del mismo Hub. |
| `self.clients.clients(ids)` | Varios identificadores, sin duplicados. |
| `self.clients.group(name)` | Miembros listos del grupo de este Hub. |

`await target.send(event, *args)` devuelve `BroadcastResult(sent, failed)`.
`sent` cuenta envíos de transporte, no la ejecución del handler del cliente.
Un fallo de destinatario no aborta los demás; un grupo vacío devuelve ceros.
Los selectores caller/others requieren contexto de conexión.

El broadcast serializa una vez por codec y utiliza como máximo
`broadcast_concurrency` workers. Comparte strings/bytes inmutables, espera el
backpressure del socket y no crea una task por cada destinatario de un broadcast
grande ni una cola de salida ilimitada.

## Invocación al cliente y emisión desde servicios

```python
state = await self.clients.client(connection_id).invoke(
    "getState", {"section": "orders"}, timeout=5,
)
```

`invoke` espera un completion correlacionado, mientras `send` sólo espera el
envío. Invoke se permite únicamente para un cliente explícito o caller; un
selector múltiple lanza `RuntimeError`. Cada conexión posee un mapa acotado de
futures, con cleanup al completar, expirar, cancelar o desconectar. Los
completions desconocidos/duplicados se ignoran.

Timeout lanza `TimeoutError`; desconexión, `ConnectionError`; un error informado
por el cliente produce `orionis.realtime.errors.ClientInvocationError` con
mensaje sanitizado. La cancelación/timeout del servidor no envía automáticamente
un `cancel` al cliente en v1; una respuesta tardía se ignora.

El provider eager y facade siguen el patrón normal de Orionis:

```python
from orionis.support.facades import Realtime

await Realtime.hub(ChatHub).group("general").send(
    "messageReceived", {"message": "Mantenimiento próximo"},
)

state = await Realtime.hub(DeviceHub).client(connection_id).invoke(
    "getState", timeout=5,
)
```

También se puede inyectar `IConnectionManager`. Facade y Hub delegan al mismo
owner, sin registros paralelos. Sustituir ese contrato es el punto de extensión
para distribución futura; no se incluye ningún backplane Redis/Kafka/etc.

**Límite multi-worker:** el registro y los broadcasts sólo abarcan el proceso o
worker actual. No hay replay, cola offline ni persistencia de mensajes.
WebSocket send/RPC = realtime no durable. Queue job = ejecución durable.

## Streaming y cancelación

```python
from collections.abc import AsyncIterator
from app.services.progress import ProgressService

class ProgressHub(Hub):
    @remote
    async def watchProgress(
        self, process_id: str, service: ProgressService,
    ) -> AsyncIterator[int]:
        async for value in service.watch(process_id):
            yield value
```

Cada valor genera `stream_item` y el final produce `stream_complete`. El runtime
espera el envío antes de solicitar el siguiente valor: no acumula el stream.
Fallo del productor/serialización genera un error terminal controlado.
`aclose()` se espera cuando el iterador lo ofrece, incluida la cancelación.
La limpieza del productor y la liberación del scope de invocación terminan
antes de enviar el envelope terminal de éxito o error.

El cliente envía `{"type":"cancel","id":"su-invocation-id"}`. Sólo se
cancela esa RPC, se ejecuta su `finally` y se cierra su scope. Un envío que ya
estaba en curso puede terminar antes del error de cancelación; no se interrumpe
la escritura compartida del socket. Desconectar cancela todo el trabajo de esa
conexión. No captures `CancelledError` para ignorarlo.

Una vez que ejecución y cleanup fijan el resultado, una cancelación que llegue
durante su entrega final no puede reemplazarlo ni generar un segundo terminal.
El cliente puede reutilizar el ID después de recibir el envelope terminal. El
servidor conserva la propiedad de la tarea de entrega hasta que termina y la
incluye en el cleanup de desconexión o shutdown.

Async generators y métodos anotados `AsyncIterable`/`AsyncIterator` no tienen
timeout de stream predeterminado. El cliente puede enviar `timeout` positivo,
finito y no mayor que `invocation_timeout`. Las llamadas ordinarias sí usan ese
timeout predeterminado. La duración de la conexión es independiente.

El deadline de invocación abarca DI, binding, ejecución, entrega de elementos
del stream y limpieza del productor. La entrega final de `completion` o
`stream_complete` ocurre después de liberar el scope y fuera de ese deadline,
respetando todavía el backpressure de red. Puede terminar después del tiempo
configurado sin producir un segundo resultado de timeout. Tanto las invocaciones
activas como las que terminan de entregar su terminal cuentan para
`max_concurrent_invocations`; un cliente lento no acumula tareas de entrega sin
límite. Si el cliente necesita un plazo para recibir el terminal, debe mantener
también su propio temporizador local.

## Configuración y arquitectura

En `config/realtime.py` usa una entidad frozen siguiendo la convención actual:

```python
from dataclasses import dataclass
from orionis.foundation.config.realtime import RealtimeConfig

@dataclass(frozen=True, kw_only=True)
class BootstrapAppRealtime(RealtimeConfig):
    max_concurrent_invocations: int = 16
    max_pending_client_invocations: int = 32
    invocation_timeout: float = 30.0
    client_result_timeout: float = 30.0
    broadcast_concurrency: int = 32
    max_groups_per_connection: int = 64
    max_message_size: int = 1024 * 1024
```

Los límites raw `http.websocket` también se aplican. El codec se selecciona con
`Route.hub(..., protocol="json" | "msgpack")`: JSON es el default y MessagePack
usa msgspec sin instalar otra dependencia. No se negocia mediante subprotocol.

Los códigos estables incluyen `method_not_found`, `invalid_arguments`,
`validation_error`, `unauthorized`, `forbidden`, `busy`, `timeout`, `cancelled`
e `internal_error`. Los mensajes no contienen tracebacks, rutas, SQL ni secretos.
Los errores estructurales del protocolo y fallos fatales cierran la conexión.
No se loguea cada mensaje ni sus payloads.

`Hub`/`HubContext`/`remote` son la API de aplicación; `RemoteMethod` conserva el
dispatch y binding; `HubProtocol` codifica/decodifica; `HubRuntime` gobierna
scopes y lifecycle; `RealtimeConnection` posee tasks/futures; `ConnectionManager`
posee conexiones y grupos; `HubClients`/`HubGroups` ofrecen selectores pequeños;
`RealtimeProvider` y `Realtime` integran el Container y facade.

El hot path usa msgspec, lookup del dispatch compilado, validación, DI y envío
esperado. La caché acotada no retiene instancias de Hub. No hay reflection de
clases por mensaje, imports controlados por la red, threads, heartbeat obligatorio,
BackgroundTask ni buffers durables. Las diferencias ASGI/RSGI permanecen en sus
adapters raw; RSGI no expone headers/subprotocol de aceptación ni detalles del
close frame. No se afirman mejoras de benchmark sin medirlas.
