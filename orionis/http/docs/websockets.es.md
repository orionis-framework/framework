# Conexiones WebSocket y respuestas en streaming

`Application` y `KernelHTTP` despachan conexiones WebSocket en ASGI
(`scope["type"] == "websocket"`) y Granian RSGI (`scope.proto == "ws"`).
Las rutas usan el compilador, parámetros convertidos, nombres, grupos y caché
existentes. Se admiten funciones, `[Controller, "method"]` y controladores
invocables. GET y WebSocket pueden compartir una ruta; WebSocket no aparece en
`Allow`/`OPTIONS` HTTP ni ejecuta el fallback HTTP.

WebSocket raw no depende de `orionis.realtime`. `WebSocket` administra estado y
concurrencia; `IWebSocketTransport` lo separa de `ASGIWebSocketTransport` y
`RSGIWebSocketTransport`, responsables de normalizar los eventos del servidor.
Un transporte propio puede implementar ese mismo contrato.

```python
from orionis.http import WebSocket
from orionis.support.facades.router import Route

async def echo(socket: WebSocket, room: int) -> None:
    await socket.accept()
    async for message in socket:
        if message.isText():
            await socket.sendText(message.text)
        elif message.isBytes():
            await socket.sendBytes(message.bytes)

Route.websocket("/rooms/{room:int}", echo).name("rooms.socket")
```

Cada conexión admitida abre un scope independiente durante toda su ejecución,
incluidos cierre y limpieza. El `WebSocket` se registra en el scope para DI;
constructores, métodos y middleware reciben la misma conexión y los mismos
servicios scoped. Otras conexiones reciben instancias independientes. Los
handlers y middleware deben devolver `None`.

El handshake aplica proxies, mantenimiento, validación de seguridad, rate limit
global y validación explícita de Origin. Por defecto se acepta el Origin que
coincide con el esquema/Host del handshake y clientes sin Origin. Otros
orígenes requieren `http.websocket.allow_origins`; `"*"` permite cualquiera.
Origin no autentica al cliente: valida credenciales y permisos antes de
`accept()`.

Las conexiones omiten el middleware HTTP de aplicación y la restauración
automática de sesión, CSRF e identidad, que dependen de Request/Response y
cookies. Para autorización o contexto propio usa `WebSocketMiddleware`,
construido por DI dentro del scope de cada conexión:

```python
from orionis.http import WebSocket, WebSocketMiddleware, WebSocketNext

class SocketGuard(WebSocketMiddleware):
    __slots__ = ()

    async def handle(self, socket: WebSocket, call_next: WebSocketNext) -> None:
        if socket.headers.get("x-access") != "expected-application-credential":
            await socket.reject(status_code=401)
            return
        await call_next()

Route.websocket("/rooms/{room:int}", echo).middleware(SocketGuard)
```

Cada continuación se puede invocar una vez. Mezclar middleware HTTP y
WebSocket en una ruta produce un error durante compilación.

| API | Comportamiento |
|---|---|
| `path`, `headers` | Metadatos del handshake. |
| `state` | `SimpleNamespace` mutable exclusivo de esta conexión. |
| `connectionState` | `CONNECTING`, `CONNECTED`, `CLOSING` o `CLOSED`. |
| `routeParams()` | Parámetros convertidos y mutables exclusivos de esta conexión. |
| `accepted`, `closed` | Estado explícito del handshake y cierre. |
| `await accept(*, subprotocol=None, headers=None)` | Acepta una vez con las opciones admitidas por el servidor. |
| `await receive()` | Devuelve un `WebSocketMessage` inmutable, incluido el evento terminal una sola vez. |
| `await receiveText()` / `receiveBytes()` | Devuelve el tipo esperado; otro tipo produce `TypeError`. |
| `await sendText(data)` / `sendBytes(data)` | Envía el tipo explícito y espera la contrapresión de red. |
| `await send(data)` | Envía texto/binario y espera al transporte; envío/cierre se serializan. |
| `await receiveJson()` / `sendJson(data)` | Deserialización/serialización JSON con msgspec. |
| `await reject(status_code=403)` | Rechaza antes de aceptar; repetir es inocuo. |
| `await close(code=1000, reason="")` | Cierra o rechaza si no estaba aceptado; repetir es inocuo. |
| `supportsCloseDetails` | Indica soporte de código/motivo personalizado en el frame de cierre. |
| `async for message in socket` | Itera mensajes de datos hasta desconexión. |

`WebSocketMessage`, `WebSocketMessageType` y `WebSocketState` se exportan desde
`orionis.http`. El mensaje es un registro frozen, slots y keyword-only con
`type`, `data`, `code` y `reason`. Conserva el payload original sin copiarlo.
Permite `isText()`, `isBytes()`, `isDisconnect()`, `.text` y `.bytes`; los accesores
tipados rechazan tipos distintos. `receive()` entrega la desconexión una sola
vez; las operaciones posteriores producen `WebSocketDisconnected`. Los helpers
tipados también lanzan esa excepción al recibir la desconexión, conservando los
datos disponibles. La iteración termina normalmente.

Enviar o recibir requiere aceptación completada. Dos lectores simultáneos
producen `RuntimeError`; no existe una cola de lectores. Envíos, aceptación y
cierre comparten un lock y esperan directamente al servidor. Cancelar un lector
libera el lock y permite otra lectura. Cancelar un escritor mientras espera el
lock afecta únicamente a ese caller. Cancelar un envío de red activo o la
aceptación deja `CLOSING`: no se conoce si la entrega terminó y el propietario
debe cerrar la conexión. La cancelación siempre se propaga. Cerrar varias veces
no genera frames duplicados, incluso si falló un cierre previo. Los errores del
servidor distintos de desconexiones explícitas permanecen visibles.

El kernel trata la desconexión como finalización normal. Otros errores
se propagan al servidor después de cerrar ASGI con código 1011. Retorno,
excepción y cancelación cierran la conexión y liberan el scope y su cupo.
La desconexión se observa al enviar/recibir; un handler inactivo debe conservar
un bucle de recepción o depender de cancelación/timeouts del servidor. No se
añade el monitor de desconexiones HTTP a estas conexiones.

```python
from orionis.foundation.config.http import HTTP, HTTPWebSocket

http = HTTP(websocket=HTTPWebSocket(
    max_connections=128,
    max_message_size=1024 * 1024,
    allow_origins=("https://client.example",),
))
```

Los defaults son 128 conexiones por kernel y 1 MiB por mensaje entrante.
La admisión tiene sincronización entre threads y rechaza inmediatamente un
exceso antes de crear otro scope. El límite es independiente de las peticiones
HTTP; un límite compartido por procesos requiere controles de deployment.
Texto se mide en bytes UTF-8. Un mensaje excesivo cierra la conexión y produce
`WebSocketDisconnected(code=1009)`. El mensaje ya fue entregado completo por el
servidor: configura también sus límites de frames/mensajes y conexiones, pues
estos checks no limitan buffers internos del servidor. No se mantiene una cola
de salida de aplicación; cada envío se espera.

ASGI permite seleccionar un subprotocolo ofrecido por el cliente. Los headers
de aceptación requieren `asgi.spec_version >= 2.1`; sin versión se asume 2.0.
Se normalizan a minúsculas y rechazan CR/LF, pseudo-headers y
`sec-websocket-protocol`; para este último se usa `subprotocol`. Solicitar
headers en un servidor anterior produce `NotImplementedError` antes del
handshake. El motivo del cierre se envía desde 2.3; versiones anteriores reciben
el código. Se conserva el motivo de desconexión cuando el servidor lo entrega.

RSGI Granian expone `close(status)`
para rechazar el handshake HTTP y cerrar la conexión de forma predeterminada;
no expone códigos/motivos del frame de cierre WebSocket. Solicitar un cierre
personalizado en RSGI produce `NotImplementedError`. Mensajes RSGI excesivos se
cierran por esa API y reportan 1009 localmente. Un rechazo ASGI devuelve HTTP
403 salvo que el servidor anuncie la extensión `websocket.http.response`, que
permite el status solicitado. RSGI sí admite el status HTTP de rechazo.
Granian 2.8.4 tiene `accept()` sin argumentos: solicitar subprotocolo o headers
no vacíos produce `NotImplementedError` antes de aceptar. Sus mensajes kind
0/1/2 se normalizan a desconexión/binario/texto. El cierre carece de código y
motivo del peer, representados por 1006/`None`. `ProtocolClosed` y errores de red
se convierten en `WebSocketDisconnected` con su causa original; `ProtocolError`
se propaga como error del servidor.

Las diferencias corresponden a las fuentes primarias
[especificación ASGI](https://asgi.readthedocs.io/en/latest/specs/www.html) y
[especificación RSGI Granian](https://github.com/emmett-framework/granian/blob/v2.8.4/docs/spec/RSGI.md).

`StreamingResponse`/`response.stream(...)` ya transmitían iterables async/sync
por chunks en ASGI y RSGI sin materializar el body. Los adapters cierran
iteradores async en `finally` si falla o se cancela el envío. `FileResponse`
usa lecturas ASGI acotadas de 64 KiB y delega archivos/rangos RSGI a Granian.
Background tasks se esperan después de un envío exitoso dentro del scope.
Iteradores sync todavía avanzan en el event loop: usa generadores async u
offload explícito si hay trabajo bloqueante. Esperar envíos streaming RSGI
tampoco garantiza por sí solo un límite de memoria del servidor; sus buffers
dependen de Granian.

`tests/http/test_websocket.py` prueba estados, texto/binario/JSON, desconexión,
límites UTF-8, DI real, aislamiento scoped, controladores, autorización,
continuaciones, admisión, Origin y limpieza ante fallo/cancelación. Las pruebas
foundation verifican dispatch ASGI/RSGI sin monitores HTTP.
`test_websocket_transport.py` agrega barreras deterministas y excepciones reales
de Granian: serialización, contrapresión, cancelación, mensajes inmutables,
negociación, capacidades no admitidas y carreras de cierre/recepción.
`test_websocket_shutdown.py` verifica la espera de tasks y limpieza de scopes
durante shutdown.

Comando ejecutado: `.venv/Scripts/python.exe reactor test --start-dir=tests/http
--file-pattern=test_websocket*.py --verbosity=0`: **47 pruebas aprobadas**,
incluidos códigos de estado y shutdown. Los módulos de producción raw pasan
Ruff y Pyright focalizados con cero diagnósticos. Se inspeccionaron directamente
las firmas instaladas y los stubs de Granian 2.8.4. Son pruebas con dobles de
protocolo; no certifican throughput ni duración prolongada.

Migración: el constructor administrado por el kernel recibe `(transport,
adapter, *, params=None, max_message_size=1048576)`. Un handler que esperaba
`str`/`bytes` desde `receive()` debe elegir `receiveText()`/`receiveBytes()` o
consultar `message.data`. Se conserva `send(str | bytes)`.
