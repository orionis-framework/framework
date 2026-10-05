# Implementación y verificación de WebSocket y Realtime

Esta entrega separa el transporte WebSocket, la API raw y la capa opcional de
Hubs. Reutiliza el Application y su Container; no introduce otro bootstrap,
protocolo SignalR, SDK público, sistema de señales ni infraestructura distribuida.

## Arquitectura y contratos

| Componente | Responsabilidad |
|---|---|
| `http/adapters/websocket/contracts/transport.py` | `IWebSocketTransport`: handshake, lectura, escritura, rechazo y cierre. |
| `http/adapters/websocket/asgi.py`, `rsgi.py` | Normalización de las interfaces reales del servidor. |
| `http/websocket.py`, `websocket_message.py` | `WebSocket`, mensajes inmutables, estado explícito y concurrencia. |
| `http/routes/enums/protocols.py` | `RouteProtocol`, independiente del tipo de action. |
| `realtime/hub.py`, `decorators.py`, `metadata.py` | Hub/contexto, exposición `@remote`, dispatch y binding compilados. |
| `realtime/protocol.py`, `errors.py` | Orionis Realtime v1, codecs msgspec y errores controlados. |
| `realtime/runtime.py`, `connection.py` | Lifecycle, scopes, tasks, streaming y correlación de resultados. |
| `realtime/manager.py`, `clients.py`, `groups.py`, `entities.py` | Registro local, targeting, grupos y `BroadcastResult`. |
| `realtime/contracts/` | Contrato sustituible del manager y vista estructural de conexión. |
| `foundation/config/realtime/` | `RealtimeConfig` frozen/slotted y validado. |
| `realtime/provider.py`, `support/facades/realtime.py` | Singleton del manager y facade `Realtime`. |

`Route.websocket` conserva funciones, controllers e invocables. `Route.hub`
registra una clase Hub y su codec. El caché de rutas pasa a versión 3 y rechaza
schemas/versiones incompatibles. HTTP no resuelve rutas WebSocket ni las incluye
en HEAD, OPTIONS o Allow; tampoco acepta `WEBSOCKET` como un verbo HTTP de red.

KernelHTTP construye el adapter apropiado, mantiene un scope por conexión,
precarga los dispatchers Hub y registra su cleanup en el shutdown existente.
El runtime Hub sólo se carga para despachar rutas Hub. Raw WebSocket no importa
ni ejecuta RPC. El provider y la configuración siguen el registro core normal.

La corrección de anotaciones de Container refleja su comportamiento existente:
`getCurrentScope()` devuelve `ScopeManager | None` y cada argumento de `call()`
es un objeto, no necesariamente un dict/tuple. No cambia su algoritmo de DI.
Auth añade una copia interna de identidad/restricciones con locks y cachés de
autorización independientes para cada invocación.

## Raw WebSocket

ASGI maneja connect/accept/receive/send/disconnect/close, subprotocolos ofrecidos,
headers de aceptación desde spec 2.1 y motivo de cierre desde 2.3. Conserva los
detalles de desconexión disponibles. RSGI usa el `accept()` y el transporte real
de Granian 2.8.4: kind 0/1/2, `send_str`, `send_bytes` y `close(status)`.

Un estado explícito impide aceptación doble, envío previo al handshake o uso
posterior al cierre. El cierre es idempotente. Los envíos se serializan mediante
lock y esperan el transporte; se rechazan dos lectores simultáneos. Cancelar una
lectura libera su ownership; cancelar un envío de red activo deja el socket en
estado de cierre, porque su entrega es incierta. Los errores inesperados del
servidor permanecen visibles.

Migración: `receive()` ahora devuelve `WebSocketMessage`; los callers antiguos
deben usar `receiveText()`, `receiveBytes()` o `message.data`. Se conserva
`send(str | bytes)`. El constructor administrado por el kernel recibe el
transporte independiente de ASGI/RSGI.

## Realtime y concurrencia

Cada conexión ejecuta onConnect/onDisconnect y cada RPC construye un Hub nuevo
por DI dentro de un scope independiente con contextvars. Constructor y método
comparten el scope de esa invocación; dos RPC concurrentes no comparten servicios
SCOPED. El contexto de conexión se registra explícitamente en cada scope.

El protocolo define ready, invoke, completion, send, stream_item,
stream_complete, cancel, ping y pong. JSON usa texto; MessagePack usa binario.
La ruta selecciona el codec. `send` espera el transporte; `invoke` también
espera un resultado lógico del cliente, con un Future propio de esa conexión.

Los selectores all/caller/others/client/clients/group usan el mismo manager.
Los grupos se aíslan por clase Hub y se eliminan al desconectar. Broadcast
serializa una vez por codec y crea como máximo `broadcast_concurrency` workers.
Un destinatario fallido no aborta los demás.

Los streams esperan cada envío antes de avanzar el productor y siempre esperan
`aclose()` cuando existe. El terminal sólo se entrega después de cerrar productor
y scope. Su escritura final queda fuera del timeout de ejecución, conservando
backpressure. Las tareas en entrega terminal siguen contando para el presupuesto
y el cleanup; liberar el ID permite reutilizarlo tras observar el resultado.
Una cancelación tardía no sustituye un resultado ya determinado.

No hay una cola ilimitada de salida. Existe como máximo una tarea de escritura
de transporte por conexión. Esto permite cancelar una RPC sin interrumpir una
escritura compartida. Disconnect cancela y espera tareas activas/finalizando,
libera Futures, elimina grupos/registro y ejecuta el hook final. Shutdown espera
cleanup cooperativo durante un máximo de cinco segundos.

## Revisión de seguridad y recursos

- La entrada de red sólo selecciona nombres en el dispatch map de `@remote`.
  No se construyen imports, atributos privados, comandos ni metadata ejecutable
  desde el payload. Aliases duplicados y firmas ambiguas fallan al registrar.
- El binder clasifica tipos cliente/DI al arrancar. Rechaza parámetros extra,
  duplicados o dirigidos a servicios. Sólo los valores filtrados y las
  dependencias resueltas internamente llegan a Application.call.
- msgspec aplica tipos estrictos. La validación de schemas Orionis atraviesa
  también colecciones y wrappers Struct usando metadata compilada, sin omitir
  reglas personalizadas ni ejecutarlas dos veces.
- Hay límites de bytes UTF-8/binarios, IDs, targets, argumentos, invocaciones,
  Futures pendientes y grupos. Las conexiones tienen el límite raw existente.
  La admisión no acumula una cola de RPC en espera.
- Los errores RPC no exponen tracebacks ni texto arbitrario de excepciones. Los
  logs de lifecycle/protocolo no incluyen automáticamente payloads o credenciales.
- Las pruebas verifican registros/grupos vacíos, ausencia de tareas/Futures
  pendientes, scopes liberados y recolección de referencias débiles. Incluyen
  cancelación inmediata, durante backpressure, antes del inicio y en shutdown.

## Verificación reproducible

Se usa el runner oficial del framework para conservar bootstrap, facades y DI:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe reactor test --start-dir=tests --verbosity=2
.venv/Scripts/python.exe -m ruff check .
uv tool run --from pyright pyright --pythonpath .venv/Scripts/python.exe
.venv/Scripts/python.exe reactor test --start-dir=tests/realtime --file-pattern=test_integration.py --verbosity=1
```

Los tests de integración ASGI y RSGI abren un servidor Granian real en loopback
y verifican handshake RFC6455, eco Unicode/binario, ready/invoke JSON y MessagePack,
RPC al cliente y cierre. El módulo de prueba contiene el cliente mínimo y genera
la aplicación y las rutas en un directorio temporal. Los procesos se liberan al
finalizar; no hay módulos auxiliares de aplicación o rutas en la carpeta de tests.

Resultados finales en este checkout, con Python 3.14 y Granian 2.8.4:

| Verificación | Resultado |
|---|---|
| Suite completa del framework | **8.574/8.574**, sin fallos, errores ni skips. |
| Nuevos métodos de prueba | **111**, además de adaptar pruebas existentes. |
| WebSocket raw, adapters y shutdown | **47/47**. |
| Realtime | **77/77**, incluidos 22 casos de runtime y 12 de conexión/RPC al cliente. |
| Routing | **218/218**. |
| Container | **253/253**. |
| Auth y schemas afectados | También incluidos y aprobados en la suite completa. |
| Granian real ASGI y RSGI | Ambos smoke tests aprobados tras el ajuste final de terminales. |
| Ruff global | **0 diagnósticos**. |
| Pyright focalizado | **42 archivos, 0 errores y 0 advertencias**. |
| Pyright global | **5.346 errores y 1 advertencia** existentes en el repositorio. |
| Comparación global de Pyright | Primera medición: 5.448 errores/1 advertencia; **0 diagnósticos añadidos**. |

La comparación de Pyright usa un multiset de archivo, mensaje, regla y severidad,
sin depender de cambios de número de línea. El repositorio no contiene una
configuración dedicada de Pyright; se usó la versión 1.1.414 con el intérprete
del proyecto. El análisis global no está limpio y esta entrega no afirma que lo
esté. El análisis focalizado incluye Realtime, sus pruebas/helpers, transportes
raw, mensajes, excepciones, configuración, contrato de protocolo y facade nueva.

La suite completa incluye HTTP, SSE, StreamingResponse, ASGI/RSGI HTTP,
foundation/bootstrap, sesiones, Auth, Container, BackgroundTask, Queue y facades.
También se verificaron imports públicos en un proceso nuevo y `git diff --check`.

## Límites conocidos

El registro es local al worker/proceso; no hay backplane, replay ni persistencia.
WebSocket send/RPC es realtime no durable; Queue sigue siendo la primitiva
durable. No se revalida automáticamente la credencial original por mensaje:
autenticación, revocación y autorización de métodos/grupos pertenecen a la
aplicación. Los contextos Auth personalizados necesitan una adaptación explícita.

RSGI 2.8.4 no expone subprotocolos/headers de aceptación ni códigos/motivos de
close frame. Opciones no admitidas fallan explícitamente; los códigos de fallo
locales no prometen aparecer en la red. Los límites de mensaje Orionis se aplican
después de recibirlo: también deben configurarse los buffers/límites del servidor.

La cancelación es cooperativa. Un método síncrono bloqueante o un handler que
suprime CancelledError impide garantizar cleanup inmediato. El framework acota
la espera de shutdown y reporta handlers que exceden el plazo.

No se afirman cifras de throughput, latencia o estabilidad de larga duración.
La verificación mide corrección; no se encontró un harness apropiado de
microbenchmarks que ampliar sin introducir infraestructura ajena a esta entrega.

Manuales: [WebSocket raw](../../http/docs/websockets.es.md),
[Hubs y ejemplos](README.es.md), [protocolo para clientes](protocol-v1.md).
