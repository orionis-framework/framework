# Crear un hub con operaciones tipadas

Usa un Hub para agrupar operaciones que comparten audiencia y protocolo. Solo métodos de instancia ordinarios marcados con `@remote` son invocables. Un método público sin ese decorador permanece fuera de la superficie remota.

## Generar un hub

```shell
python -B reactor make:realtime-hub chat
```

Crea `app/realtime/hubs/chat_hub.py` con `ChatHub(Hub)` y un método asíncrono `echo(message: str) -> str` marcado con `@remote`. Regístralo explícitamente en tus rutas WebSocket:

```python
from app.realtime.hubs.chat_hub import ChatHub
from orionis.support.facades import Route

Route.hub("/realtime/chat", ChatHub)
```

El generador respeta `app_realtime_hubs`, admite subcarpetas y no sobrescribe archivos existentes. El sufijo `Hub` se añade una sola vez. Para conexiones de texto sin RPC usa `make:realtime-socket`, descrito en [WebSocket](../../../http/docs/es/websockets.md).

## Operaciones tipadas

```python
import asyncio
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub

class MathHub(Hub):
    @remote(name="sum")
    async def add(self, first: int, second: int = 2) -> int:
        return first + second

methods = compile_hub(MathHub)
assert asyncio.run(methods["sum"].bind([3], {})) == {"first": 3, "second": 2}
```

El ejemplo puede compilarse sin servidor. Para servirlo declara `Route.hub("/realtime/math", MathHub)` desde rutas, importando Route de `orionis.support.facades`. `protocol="msgpack"` selecciona MessagePack binario para toda la conexión; el default es JSON texto. La selección no se negocia por cada mensaje.

## Datos y servicios

Anota cada argumento remoto. Tipos de datos compatibles con msgspec se convierten desde argumentos del cliente; tipos de servicios se resuelven con el contenedor y no pueden ser suplantados por un valor del payload. Los schemas Orionis anidados, incluidos los contenidos en colecciones o structs ordinarios, ejecutan sus reglas síncronas o asíncronas antes del despacho. Las llamadas directas a `bind()` requieren `await`; dentro de un loop existente usa `await methods["sum"].bind([3], {})`. Se admiten defaults y parámetros keyword-only.

Para un servicio de aplicación importable `Calculator`, un método puede declarar `async def add(self, first: int, calculator: Calculator, second: int = 2) -> int`. Registra/resuelve Calculator normalmente en el contenedor. Mantén el import disponible en runtime cuando la reflexión lo requiera; no escondas todas las anotaciones de inyección en `TYPE_CHECKING` sin una estrategia de resolución.

La compilación rechaza nombres privados, aliases duplicados, classmethods/staticmethods, posicionales exclusivos, variádicos y anotaciones ambiguas. Un alias debe ser identificador público Python de hasta 128 caracteres. Un fallo en registro es preferible a exponer una firma cuya propiedad de datos no está clara.

## Contexto y ciclo de vida

Cada invocación recibe una instancia fresca con `context`, `clients` y `groups`. `context.connection_id` identifica conexión, `.socket` da acceso a WebSocket y `.user` contiene la identidad establecida por el pipeline. No uses atributos de la instancia para conservar estado entre invocaciones. Usa servicios de dominio o el registro adecuado.

`onConnect()` corre tras registrar conexión y antes de anunciar disponibilidad; puede unirse a grupos o rechazar preparación. `onDisconnect(code, reason)` corre después de cancelar trabajo propio y retirar el registro. Libera recursos de aplicación de forma idempotente. El decorador controla exposición, no permisos; comprueba autorización de operaciones además de proteger handshake cuando corresponda.

## Fallos deliberados

Para una condición de negocio visible al cliente importa `RPCError` desde `orionis.realtime.errors` y lanza `RPCError("conflict", "Operation is no longer available")`. El runtime sanea fallos internos, validación, autorización, timeout y cancelación a códigos estables. No envíes tracebacks o errores del proveedor como mensajes públicos.

Evidencia: [Hub](../../hub.py), [decorador](../../decorators.py), [compilación](../../metadata.py), [runtime](../../runtime.py). Pruebas: [metadata](../../../../tests/realtime/test_metadata.py), [kernel](../../../../tests/realtime/test_kernel.py), [runtime](../../../../tests/realtime/test_runtime.py). Continúa con [protocolo](protocol-and-streaming.md).
