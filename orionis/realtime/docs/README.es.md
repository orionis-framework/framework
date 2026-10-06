# orionis.realtime

> `orionis.realtime` agrega RPC tipado y bidireccional y entrega de eventos a rutas WebSocket Orionis.

## Descripción general

Las rutas enlazan una clase `Hub` a un endpoint WebSocket nativo con frames de texto JSON o binarios MessagePack. Solo métodos de instancia marcados con `@remote` son invocables. Orionis compila argumentos, schemas, DI y streaming al registrar, y crea una instancia nueva de hub por invocación.

Cada conexión posee invocaciones acotadas, resultados pendientes, grupos y escrituras ordenadas. El `ConnectionManager` predeterminado es local al worker; ofrece selección aislada por hub y broadcasts acotados, sin fingir ser un backplane distribuido.

## Requisitos

- Python 3.14 o posterior.
- Aplicación HTTP Orionis iniciada con servidor ASGI/RSGI compatible con WebSocket.
- Registro `Route.hub(...)` con `json` o `msgpack`.
- Argumentos/resultados serializables; valores `Schema` también pasan validación Orionis.

## Inicio rápido

```python
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub


class MathHub(Hub):
    @remote
    async def add(self, first: int, second: int) -> int:
        return first + second


methods = compile_hub(MathHub)
assert tuple(methods) == ("add",)
assert methods["add"].bind([2, 3], {}) == {"first": 2, "second": 3}
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

## Conceptos principales

### Superficie remota explícita

`@remote` adjunta metadata sin envolver la función. El nombre debe ser identificador público de máximo 128 caracteres; un alias opcional controla el target wire. Se rechazan métodos class/static, privados, aliases duplicados, parámetros positional-only/variadic, anotaciones ausentes y mezcla ambigua de servicio/datos.

### Binding de argumentos y DI

Los parámetros del cliente son datos tipados compatibles con `msgspec`; dependencias del contenedor se resuelven aparte y el cliente no puede suplirlas. Hay defaults y keyword-only. Schemas anidados ejecutan validación del framework tras conversión.

### Ciclo de invocación

El cliente envía `invoke`, puede enviar `cancel` y recibe `completion` o `stream_item` seguidos de `stream_complete`. Invocaciones escalares usan timeout default salvo override. Streams no tienen límite default, pero respetan uno explícito. Cleanup cancela y espera trabajo propio.

### Llamadas bidireccionales

Métodos hub envían eventos e invocan un cliente esperando `completion`. Los resultados pendientes están acotados y tienen deadline. El texto de error del cliente se convierte en `ClientInvocationError` saneado.

### Grupos y procesos

Los grupos se aíslan por clase Hub y se limpian al desconectar. El registro incluido solo conoce conexiones del worker actual; reemplace `IConnectionManager` o añada backplane para broadcast entre workers.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `hub.py`, `decorators.py`, `metadata.py` | Lifecycle, marcadores y planes de dispatch. |
| `runtime.py`, `connection.py` | Loop WebSocket, tareas, correlación, cleanup y escritura. |
| `protocol.py` | Envelopes estrictos Realtime v1 JSON/MessagePack. |
| `clients.py`, `groups.py` | Selección, eventos, RPC cliente y membresía. |
| `manager.py` | Registro local y broadcasts acotados. |
| `entities.py`, `errors.py` | Resultado y errores seguros. |
| `provider.py`, `config.py` | DI, fachada y configuración. |
| `contracts/` | Límites reemplazables de conexión/manager. |

## API pública

La raíz exporta de forma diferida `Hub`, `HubContext`, `remote`, `HubProtocol`, `HubClients`, `HubGroups`, `ConnectionManager` y `BroadcastResult`.

### `Hub`

`onConnect()` corre tras registrar y antes del envelope ready; puede unir grupos o rechazar. `onDisconnect(code, reason)` corre tras liberar invocaciones/registros. Por invocación Orionis asigna `context`, `clients` y `groups` en un Hub nuevo.

### Selección de clientes

`HubClients` expone `.all`, `.caller`, `.others`, `.client(id)`, `.clients(ids)` y `.group(name)`. Todo target admite `send`; solo `.client(...)` o `.caller` admite `invoke` porque necesita un resultado correlacionado.

### Acceso desde servicios

`Realtime.hub(MyHub)` devuelve `HubClients` sin caller para controladores, jobs o listeners. Selectores del caller no están disponibles fuera de una invocación.

### Fallos seguros

Lance `RPCError(code, message)` para un fallo deliberado visible. Auth, validación, cancelación, timeout, target desconocido e internos usan códigos saneados; detalles inesperados no se envían.

## Flujos de trabajo comunes

### Registrar ruta

Use `Route.hub("/realtime", MyHub)` para JSON o `protocol="msgpack"`. El codec define el frame para toda la conexión; JSON rechaza binario y MessagePack texto.

### Emitir evento

Dentro del hub seleccione all/caller/others/clientes/grupo y espere `.send(...)`. El resultado cuenta entregas/fallos; no persiste mensajes offline.

### Transmitir resultados

Devuelva `AsyncIterator`/`AsyncIterable` o generador async. Cada item se envía bajo backpressure. Cancelación/desconexión cierra iterador y libera id.

### Invocar cliente

Espere `clients.caller.invoke(...)` o `clients.client(id).invoke(...)`. El reader sigue activo para correlacionar. Use timeout apropiado.

## Ejemplos

### Crear alias y compilar stream

```python
from collections.abc import AsyncIterator
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub


class FeedHub(Hub):
    @remote(name="updates")
    async def stream_updates(self, count: int) -> AsyncIterator[int]:
        for value in range(count):
            yield value


method = compile_hub(FeedHub)["updates"]
assert method.method_name == "stream_updates"
assert method.is_stream is True
assert method.bind([], {"count": 2}) == {"count": 2}
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Codificar envelopes Realtime v1

```python
import msgspec
from orionis.realtime import HubProtocol

json_protocol = HubProtocol("json", max_message_size=4096)
msgpack_protocol = HubProtocol("msgpack", max_message_size=4096)
envelope = {"type": "send", "target": "refresh", "args": [1]}

text = json_protocol.encode(envelope)
binary = msgpack_protocol.encode(envelope)
assert isinstance(text, str)
assert isinstance(binary, bytes)
assert msgspec.json.decode(text)["target"] == "refresh"
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Construir límites validados

```python
from orionis.realtime.config import RealtimeConfig

config = RealtimeConfig(
    max_message_size=64 * 1024,
    max_concurrent_invocations=8,
    max_pending_client_invocations=16,
    invocation_timeout=10.0,
    client_result_timeout=5.0,
    broadcast_concurrency=12,
    max_groups_per_connection=20,
)
assert config.max_message_size == 65_536
assert config.broadcast_concurrency == 12
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Emitir con seguridad a un registro local vacío

```python
import asyncio
from orionis.realtime import ConnectionManager
from orionis.realtime.config import RealtimeConfig


async def example() -> None:
    manager = ConnectionManager(RealtimeConfig())
    result = await manager.hub(MathHub).all.send("refresh", {"version": 1})
    assert result.sent == 0
    assert result.failed == 0


asyncio.run(example())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Registrar rutas y emitir desde aplicación

```python
from orionis.support.facades import Realtime, Route

Route.hub("/realtime/math", MathHub)
Route.hub("/realtime/feed", FeedHub, protocol="msgpack")


async def notify_refresh() -> None:
    await Realtime.hub(MathHub).all.send("refresh", {"version": 2})
```

Validación: **Importación y sintaxis validadas** en CPython 3.14.6; registro y entrega requieren aplicación iniciada.

## Configuración

| Variable | Predeterminado | Ámbito |
|---|---:|---|
| `REALTIME_MAX_MESSAGE_SIZE` | 1 MiB | Bytes entrantes. |
| `REALTIME_MAX_CONCURRENT_INVOCATIONS` | 16 | Llamadas cliente-servidor por conexión. |
| `REALTIME_MAX_PENDING_CLIENT_INVOCATIONS` | 32 | Resultados cliente pendientes. |
| `REALTIME_INVOCATION_TIMEOUT` | 30s | Timeout escalar default. |
| `REALTIME_CLIENT_RESULT_TIMEOUT` | 30s | Deadline de resultado cliente. |
| `REALTIME_BROADCAST_CONCURRENCY` | 32 | Envíos concurrentes locales. |
| `REALTIME_MAX_GROUPS_PER_CONNECTION` | 64 | Membresías por conexión. |

Conteos/bytes son enteros positivos y timeouts segundos positivos finitos. `RealtimeProvider` carga una vez `RealtimeConfig` inmutable.

## Integración con Orionis

`Route.hub` guarda Hub/protocolo en la ruta. El kernel HTTP actualiza la conexión, autentica en su ámbito y delega a `HubRuntime`. El provider enlaza config y `IConnectionManager` reemplazable y fija `Realtime`.

El contenedor construye cada invocación, resuelve servicios y expone identidad como `HubContext.user`. Middleware/auth protegen el handshake; `@remote` controla exposición, no autorización por sí solo.

## Errores y casos límite

- Envelopes inválidos cierran con 1002; frame erróneo 1003; exceso de tamaño 1009.
- IDs son ASCII imprimible sin espacios. Targets son identificadores públicos; máximo 64 argumentos posicionales y 64 named.
- Completions desconocidos/duplicados se ignoran.
- Un fallo de escritura cierra y cancela al owner para preservar orden.
- Fallo de `onConnect` impide ready. Cleanup es idempotente y limpia grupos.
- Broadcast toma ids y vuelve a comprobar disponibilidad; desconexiones cuentan como fallo.
- `BroadcastResult` confirma entrega al socket, no manejo por el cliente.

## Rendimiento y concurrencia

Reflexión, tipos y schemas se cachean hasta 1024 Hubs. Codecs se reutilizan y broadcast codifica una vez por codec. Un lock de escritura preserva orden y backpressure.

Límites por conexión y workers de broadcast acotan memoria/tareas. Invocaciones son independientes y no comparten Hub. El manager default debe usarse en el event loop de aplicación y no sincroniza procesos.

## Compatibilidad

El envelope Orionis Realtime es versión 1 y no es SignalR. JSON usa mensajes texto; MessagePack binarios. Los adaptadores ASGI y RSGI están cubiertos. El cliente debe implementar los envelopes que use: ready, invoke, completion, cancel, ping/pong, send y stream.

## Notas de verificación

- `tests/realtime`: **79 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Se compilaron seis programas bilingües; cinco programas autónomos se ejecutaron correctamente.
- Rutas/fachada se validaron por importación/sintaxis porque requieren router iniciado y conexiones vivas.
- La evidencia cubrió wire JSON/MessagePack, sockets ASGI/RSGI, metadata, DI, auth, grupos, broadcast, resultados bidireccionales, cancelación, streaming, cleanup y límites.

