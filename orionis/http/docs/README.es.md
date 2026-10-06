# orionis.http

> `orionis.http` es la capa independiente del transporte de HTTP y WebSocket de Orionis: solicitudes, respuestas, rutas, middleware, parsing de payloads, streaming y adaptadores de protocolo.

## Descripción general

El paquete normaliza el tráfico ASGI y RSGI en una única API `Request` y convierte los objetos `Response` de Orionis en mensajes específicos del servidor. Su kernel resuelve rutas compiladas, construye pipelines de middleware, invoca controladores, procesa fallos y entrega respuestas ordinarias, streaming, archivos, eventos enviados por servidor y WebSocket.

El código de aplicación normalmente importa los tipos de solicitud/respuesta desde `orionis.http`, declara rutas mediante la facade `Route` e implementa `BaseMiddleware`. Las clases de bajo nivel para payloads y rutas están disponibles desde sus subpaquetes para infraestructura y pruebas enfocadas.

## Requisitos

- Python 3.14 o posterior.
- Un servidor ASGI o RSGI compatible con Orionis para tráfico real.
- Una aplicación Orionis iniciada para las facades `Route`, `View`, sesión, autenticación y demás servicios del contenedor.
- Límites finitos de cuerpo, multipart, concurrencia y WebSocket adecuados para el despliegue.

## Inicio rápido

```python
import json
from orionis.http import response

result = response.json(
    {"ok": True, "message": "ready"},
    status_code=201,
    headers={"X-Request-ID": "demo-1"},
)
assert result.getStatusCode() == 201
assert json.loads(result.getBody()) == {"ok": True, "message": "ready"}
assert result.getHeader("x-request-id") == ["demo-1"]
print(result.getMediaType())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

## Conceptos principales

### Normalización de solicitudes

`Request` expone `method`, `scheme`, `path`, `url`, `baseUrl`, `headers`, `queryParams`, `cookies`, datos de dirección del cliente, ayudas de autorización, parámetros de ruta y `state` mutable por solicitud. Los métodos del cuerpo incluyen `stream()`, `body()`, `text()`, `json()`, `xml()`, `msgpack()`, `formUrlEncoded()`, `form()`, `payload()` y el diccionario normalizado `data()`.

El stream del cuerpo admite un solo consumidor salvo que quepa en el búfer configurado. Las ayudas específicas por tipo de contenido rechazan tipos incompatibles en vez de adivinarlos silenciosamente. `wantsJson()`, `wantsHtml()`, `wantsXml()`, `accepts()` e `isAjax()` inspeccionan las preferencias del cliente.

### Respuestas y entrega

`Response` almacena un cuerpo de bytes o stream asíncrono de bytes, estado, cabeceras, tipo de medio opcional, cookies, datos flash y una `BackgroundTask` opcional. Las respuestas especializadas cubren HTML, texto, JSON, redirecciones, streams, SSE y archivos. Los adaptadores de transporte controlan la entrega ASGI/RSGI; el código de aplicación no emite mensajes de protocolo directamente.

### Rutas y middleware

Las rutas aceptan callables, clases de controlador invocables o `[Controller, "method"]`. Los constructores fluidos agregan nombres, middleware, exclusiones, prefijos y el perfil sin estado `public()`. El compilador separa rutas estáticas y dinámicas y admite parámetros tipados como `{id:int}`. El middleware HTTP recibe un `call_next` sin argumentos; el middleware WebSocket usa una continuación de conexión equivalente.

### Conexiones de larga duración

`EventStreamResponse` codifica perezosamente valores `ServerSentEvent` y elimina cabeceras orientadas a buffering. `WebSocket` normaliza texto, bytes, JSON, estado de cierre y detalles de desconexión sobre cualquiera de las interfaces de servidor. La conexión debe aceptarse antes de transferir datos y puede rechazarse durante el handshake.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `request.py` | Metadatos unificados, negociación de contenido y decodificación del cuerpo. |
| `responses.py`, `factory.py`, `sse.py` | Respuestas, factory compartida, archivos, streams y frames SSE. |
| `middleware.py`, `kernel.py` | Contrato de middleware, pipeline, despacho y manejo de errores. |
| `routes/` | Declaración, grupos, compilación, resolución, carga y caché de rutas. |
| `payload/` | Streams acotados, cabeceras/cookies/query estructurados, formularios y uploads. |
| `adapters/` | Adaptadores ASGI/RSGI para solicitudes, respuestas, archivos/rangos, streams y WebSocket. |
| `websocket.py`, `websocket_message.py` | API de conexión, estado y mensajes normalizados. |
| `layer/` | CORS, hosts, proxies, mantenimiento, rate limits, sesiones y CSRF. |
| `default/` | Páginas de error, handlers de salud/estáticos y controladores de autenticación opcionales. |
| `contracts/`, `enums/`, `exceptions/` | Interfaces estables, valores de protocolo/estado y errores del dominio. |

## API pública

La raíz del paquete exporta `Request`, `Response`, `ResponseTemplate`, `HTMLResponse`, `PlainTextResponse`, `JSONResponse`, `RedirectResponse`, `StreamingResponse`, `EventStreamResponse`, `FileResponse`, `ResponseFactory`, la instancia compartida `response`, `ServerSentEvent`, `BaseMiddleware`, `NextCallable`, `WebSocket`, `WebSocketMiddleware`, `WebSocketNext`, `WebSocketMessage`, `WebSocketMessageType`, `WebSocketState`, `WebSocketDisconnected` y el alias de tipo `HttpResponse`.

### `ResponseFactory`

- `view(template, **context)` devuelve un `PendingView` esperable.
- `html`, `text` y `json` construyen respuestas tipadas en memoria.
- `redirect(url, status_code=302)` solo acepta códigos de redirección.
- `stream(content, ..., media_type=None)` consume iterables síncronos o asíncronos de bytes.
- `eventStream(content, ...)` consume strings o valores `ServerSentEvent`.
- `file(path, ..., filename=None, chunk_size=65536)` transmite un archivo regular.
- `download(path, filename=None, ...)` agrega disposición de adjunto.
- `noContent(status_code=204)` y `make(...)` cubren respuestas vacías y genéricas.

### Mutación de respuestas

Use `addHeader`, `setHeader`, `getHeader`, `hasHeader`, `removeHeader`, `setCookie` y `deleteCookie`. `withCookie`, `withCookies`, `withoutCookie`, `withFlash`, `withInput` y `withErrors` devuelven la misma respuesta para encadenar. Los adaptadores leen `getBody`, `getStream`, `getRawHeaders`, estado, tipo de medio y `runBackground()`.

### Rutas

`orionis.support.facades.Route` proporciona `get`, `post`, `put`, `patch`, `delete`, `query`, `view`, `websocket`, `hub`, `group`, `fallback` y `auth`. Los constructores exponen `name`, `public`, `middleware`, `withOutMiddleware`, `prefix` y `action` diferida. Estas llamadas requieren el router registrado en una aplicación iniciada.

### Estructuras de payload

`Headers`, `QueryParams` y `Cookies` son vistas de solo lectura conscientes de mayúsculas o del protocolo. `FormData` conserva campos y archivos repetidos. `UploadedFile` expone `size`, `extension`, `read`, `chunks`, `replace`, `save` y `close`; los uploads grandes pasan a un archivo temporal al alcanzar el umbral configurado.

## Flujos de trabajo comunes

### Declarar rutas de aplicación

Ubique las declaraciones en los archivos de rutas de la aplicación cargados como `web` o `api`. Nombre las rutas cuando otro subsistema deba generar sus URL. Agrupe constructores ya declarados para heredar prefijo y middleware. Use `public()` solo para endpoints que no emplean credenciales por cookie: las capas globales de hosts, CORS, seguridad y rate limit continúan ejecutándose.

### Interpretar entrada del cliente

Prefiera la ayuda que coincide con el `Content-Type` declarado. Use `await request.data()` cuando corresponda un mapping normalizado y `await request.payload()` cuando deban conservarse valores escalares o estructurados JSON/MessagePack. Cierre `FormData` multipart después de usarlo para liberar uploads temporales.

### Devolver contenido

Devuelva `response.json(...)` para APIs, una vista esperada para plantillas, `response.redirect(...)` después de cambios de estado y `response.noContent()` para un éxito sin cuerpo. Los streams deben producir bytes; SSE puede producir strings o eventos tipados. El trabajo en segundo plano se ejecuta solo después de limpiar la entrega.

### Manejar WebSockets

Inspeccione `socket.path`, `headers`, `routeParams()` y `state`; después llame `await socket.accept()` antes de enviar o recibir. Use las ayudas tipadas, maneje `WebSocketDisconnected` y cierre explícitamente al terminar el handler. El middleware de conexión puede rechazar antes de aceptar.

## Ejemplos

### Agregar cabeceras y cookies

```python
from orionis.http import PlainTextResponse

result = PlainTextResponse("accepted", status_code=202)
result.setHeader("X-Mode", "demo")
result.setCookie("session_hint", "present", http_only=True, same_site="lax")
assert result.getBody() == b"accepted"
assert result.getHeader("x-mode") == ["demo"]
assert result.hasHeader("set-cookie")
print(result.getStatusCode())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Transmitir fragmentos de bytes

```python
import asyncio
from orionis.http import response


async def main() -> None:
    result = response.stream([b"orion", b"is"], media_type="application/octet-stream")
    chunks = [chunk async for chunk in result.getStream()]
    assert b"".join(chunks) == b"orionis"
    print(result.hasStream())


asyncio.run(main())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Codificar un evento enviado por servidor

```python
from orionis.http import ServerSentEvent

event = ServerSentEvent(
    event="progress",
    id="job-7",
    retry=1500,
    data="step 1\nstep 2",
)
frame = event.encode()
assert b"event: progress\n" in frame
assert b"data: step 1\ndata: step 2\n\n" in frame
print(frame.decode("utf-8"))
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Compilar una ruta tipada

```python
from orionis.http.routes.route_compiler import RouteCompiler

is_static, pattern, converters = RouteCompiler.compilePath("/users/{id:int}")
assert not is_static and pattern is not None
match = pattern.fullmatch("/users/42")
assert match is not None
assert converters["id"](match.group("id")) == 42
print(pattern.pattern)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Inspeccionar un mensaje WebSocket normalizado

```python
from orionis.http import WebSocketMessage, WebSocketMessageType

message = WebSocketMessage(type=WebSocketMessageType.TEXT, data="hello")
assert message.isText()
assert not message.isBytes()
assert message.text == "hello"
print(message.type.value)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Implementar middleware HTTP

```python
from orionis.http import BaseMiddleware, Request, Response


class RequestIdMiddleware(BaseMiddleware):
    async def handle(self, request: Request, call_next) -> Response:
        result = await call_next()
        result.setHeader("X-Request-ID", request.state.request_id)
        return result
```

Validación: **Importación y sintaxis verificadas** en CPython 3.14.6; la ejecución pertenece al pipeline del kernel iniciado.

## Configuración

`config/http.py` construye la entidad inmutable `BootstrapHTTP`. Los grupos y variables de entorno importantes son:

| Grupo | Variables de entorno | Valores predeterminados / propósito |
|---|---|---|
| Cuerpo | `HTTP_MAX_BODY_SIZE`, `HTTP_MAX_BUFFER_SIZE`, `HTTP_MAX_CONCURRENT_REQUESTS` | Cuerpo de 16 MiB, búfer de 2 MiB y 128 solicitudes concurrentes por worker. |
| Multipart | `HTTP_MAX_FILES`, `HTTP_MAX_FIELDS`, `HTTP_MAX_PART_SIZE`, `HTTP_MAX_FIELD_SIZE`, `HTTP_MAX_PART_HEADER_SIZE`, `HTTP_UPLOAD_MEMORY_THRESHOLD`, `HTTP_MAX_MULTIPART_MEMORY_SIZE` | Acota cantidades, tamaños, cabeceras, memoria y volcado a disco. |
| Desconexiones | `HTTP_MONITOR_DISCONNECTS` | Desactivado; habilita cancelación de solicitudes al desconectar. |
| WebSocket | `WEBSOCKET_MAX_CONNECTIONS`, `WEBSOCKET_MAX_MESSAGE_SIZE`, `WEBSOCKET_ALLOW_ORIGINS` | 128 conexiones, mensajes de 1 MiB y política same-origin salvo configuración. |
| Proxies/hosts | `TRUSTED_PROXIES`, `ALLOWED_HOSTS` | Confía por defecto en el proxy local; la lista vacía permite todo host. |
| Rate limit | `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, `RATE_LIMIT_STORE`, `RATE_LIMIT_MAX_KEYS`, `RATE_LIMIT_MAX_EVENTS`, `RATE_LIMIT_REDIS_URL`, `RATE_LIMIT_REDIS_PREFIX`, `RATE_LIMIT_REDIS_TIMEOUT` | Desactivado; 100 solicitudes por 60 segundos al habilitar; memoria o Redis. |
| CORS | `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `CORS_EXPOSE_HEADERS`, `CORS_ALLOW_CREDENTIALS`, `CORS_MAX_AGE` | Política cross-origin explícita; credenciales desactivadas; preflight de 600 segundos. |
| CSRF | `CSRF_ENABLED`, `CSRF_TOKEN_LENGTH`, `CSRF_SESSION_KEY`, `CSRF_XSRF_COOKIE`, `CSRF_COOKIE_NAME`, `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_SAME_SITE`, `CSRF_COOKIE_PATH`, `CSRF_COOKIE_DOMAIN` | Activo en rutas web con estado; tokens de 32 bytes y cookie lax. |

## Integración con Orionis

La aplicación de foundation inicia `RouterProvider`, carga `routes/web.py` y `routes/api.py`, compila y opcionalmente guarda en caché sus declaraciones y entrega el resultado a `KernelHTTP`. El kernel resuelve controladores y middleware mediante el contenedor, inyecta parámetros validados, usa servicios de sesión/autenticación para rutas con estado y delega fallos al servicio de respuestas predeterminadas.

Los módulos de vistas, validación, sesión, autenticación, tareas en segundo plano, hubs realtime, caché, logging y fallos confluyen en este límite. Los adaptadores ASGI y RSGI comparten intencionalmente semántica de solicitud y respuesta para mantener los controladores independientes del servidor.

## Errores y casos límite

- Códigos de respuesta, cabeceras, cookies, redirecciones, campos SSE o fragmentos de stream inválidos producen `TypeError` o `ValueError` temprano.
- Un cuerpo no almacenado ya consumido no puede leerse por segunda vez; los payloads que exceden los presupuestos son rechazados.
- Las ayudas JSON, XML, MessagePack, form y multipart rechazan contenido incompatible o malformado.
- Rutas estáticas duplicadas, colisiones estructurales dinámicas, nombres duplicados para paths diferentes, un segundo fallback y acciones sin asignar fallan durante registro o compilación.
- Los parámetros que no satisfacen su conversor no coinciden; método incorrecto se distingue de ruta inexistente.
- Las respuestas de archivo requieren un archivo regular existente y los adaptadores soportan entrega condicional y por rangos.
- Los campos SSE impiden inyección de saltos de línea en `event` e `id`; retry debe ser entero no negativo.
- WebSocket aplica estado de conexión, tamaño de mensaje, política de origen y capacidad; el cierre remoto produce `WebSocketDisconnected` cuando corresponde.
- Las cabeceras forwarded solo cambian la identidad si el peer inmediato está configurado como proxy confiable.

## Rendimiento y concurrencia

Los límites de tamaño y buffering se aplican durante la lectura, y el parsing multipart es incremental con cantidades acotadas de campos y archivos. Los uploads grandes pueden pasar a disco; dimensione memoria y almacenamiento temporal. Los gates por worker para solicitudes y WebSockets rechazan exceso de trabajo inmediatamente en lugar de crear una cola ilimitada.

Las rutas estáticas usan lookup por diccionario; las dinámicas se precompilan, ordenan por especificidad e indexan para resolver. `ResponseTemplate` reutiliza cuerpos y cabeceras inmutables codificados y crea respuestas mutables independientes. Streams, archivos y SSE se consumen perezosamente y propagan cancelación/limpieza. Los iterables síncronos pueden necesitar ejecutor; no bloquee el event loop dentro de generadores o middleware.

## Compatibilidad

Orionis declara Python 3.14+. La capa pública soporta adaptadores ASGI y RSGI, metadatos HTTP/1.x y metadatos HTTP/2 dependientes del servidor cuando se suministran. El soporte de detalles de cierre WebSocket varía según la interfaz y se expone mediante `supportsCloseDetails`. JSON usa UTF-8 y maneja tipos comunes de Python; la entrada MessagePack depende del conjunto de dependencias instalado con Orionis.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, parsing de solicitudes, familias de respuesta, declaración/compilación/resolución de rutas, pipelines de middleware, entidades de configuración, capas de seguridad, adaptadores ASGI/RSGI, comportamiento WebSocket/SSE e integraciones. Las **902** pruebas de `tests/http` pasaron con el runner de Orionis. Cinco ejemplos independientes se ejecutaron correctamente; la definición de middleware se validó por importación y sintaxis porque su invocación pertenece al kernel iniciado.
