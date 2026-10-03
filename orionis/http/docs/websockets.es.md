# Conexiones WebSocket y respuestas en streaming

`Application` y `KernelHTTP` despachan conexiones WebSocket en ASGI
(`scope["type"] == "websocket"`) y Granian RSGI (`scope.proto == "ws"`).
Las rutas usan el compilador, parámetros convertidos, nombres, grupos y caché
existentes. Se admiten funciones, `[Controller, "method"]` y controladores
invocables. GET y WebSocket pueden compartir una ruta; WebSocket no aparece en
`Allow`/`OPTIONS` HTTP ni ejecuta el fallback HTTP.

```python
from orionis.http import WebSocket, WebSocketDisconnected
from orionis.support.facades.router import Route

async def echo(socket: WebSocket, room: int) -> None:
    await socket.accept()
    try:
        while True:
            await socket.send(await socket.receive())
    except WebSocketDisconnected:
        return

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
| `routeParams()` | Parámetros convertidos y mutables exclusivos de esta conexión. |
| `accepted`, `closed` | Estado explícito del handshake y cierre. |
| `await accept()` | Acepta una vez; enviar/recibir antes produce `RuntimeError`. |
| `await receive()` | Devuelve `str` o `bytes`; admite un receptor concurrente. |
| `await send(data)` | Envía texto/binario y espera al transporte; envío/cierre se serializan. |
| `await receiveJson()` / `sendJson(data)` | Deserialización/serialización JSON con msgspec. |
| `await reject(status_code=403)` | Rechaza antes de aceptar; repetir es inocuo. |
| `await close(code=1000, reason="")` | Cierra o rechaza si no estaba aceptado; repetir es inocuo. |

La desconexión produce `WebSocketDisconnected(code, reason)` cuando el protocolo
ofrece esos datos y el kernel la trata como finalización normal. Otros errores
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

ASGI transmite códigos/motivos de cierre. RSGI Granian expone `close(status)`
para rechazar el handshake HTTP y cerrar la conexión de forma predeterminada;
no expone códigos/motivos del frame de cierre WebSocket. Solicitar un cierre
personalizado en RSGI produce `NotImplementedError`. Mensajes RSGI excesivos se
cierran por esa API y reportan 1009 localmente. Un rechazo ASGI devuelve HTTP
403 salvo que el servidor anuncie la extensión `websocket.http.response`, que
permite el status solicitado. RSGI sí admite el status HTTP de rechazo.
La API compartida no expone negociación de subprotocolos ni headers de
aceptación personalizados: `accept()` RSGI no recibe esos parámetros.

Las diferencias corresponden a las fuentes primarias
[especificación ASGI](https://asgi.readthedocs.io/en/latest/specs/www.html) y
[especificación RSGI Granian](https://github.com/emmett-framework/granian/blob/master/docs/spec/RSGI.md).

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
foundation verifican dispatch ASGI/RSGI sin monitores HTTP. El runner
`python -m benchmarks.runtime_load --seconds 0.1 --concurrency 1 --scenarios plain`
también ejecuta probes TCP reales contra Granian ASGI/RSGI: HTTP 101 y digest
de aceptación, eco de texto/binario enmascarado y frame de cierre del servidor.
Guarda `websocket_probe` en los resultados. Es evidencia de integración del
protocolo; no certifica throughput WebSocket ni soak de larga duración.
