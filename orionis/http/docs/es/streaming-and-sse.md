# Streaming y eventos del servidor

Un stream evita construir un cuerpo completo en memoria y permite entregar resultados a medida que se producen. Úsalo para exportaciones o progreso. No elimina el costo de producir datos, la capacidad de conexiones ni los límites del servicio remoto.

## Entregar bytes progresivamente

```python
import asyncio
from orionis.http import response

async def export_rows():
    yield b"id,name\n"
    yield b"1,Ada\n"

async def example():
    result = response.stream(export_rows(), media_type="text/csv")
    assert b"".join([chunk async for chunk in result.getStream()]) == b"id,name\n1,Ada\n"

asyncio.run(example())
```

`stream()` admite iterables síncronos y asíncronos de bytes. Un generador que produce `str` es inválido para esta API. Codifica cada fragmento con la codificación escogida. Un generador síncrono puede necesitar ejecución delegada durante el envío: mantén claro dónde ocurre el trabajo bloqueante.

## Publicar progreso como SSE

```python
from orionis.http import ServerSentEvent, response

async def progress_events():
    for step in range(3):
        yield ServerSentEvent(event="progress", id=str(step), data=str(step))

async def progress():
    return response.eventStream(progress_events())

frame = ServerSentEvent(event="progress", id="7", retry=1500, data="ready").encode()
assert b"event: progress\n" in frame
assert frame.endswith(b"\n\n")
```

`eventStream()` acepta strings y `ServerSentEvent`. El tipo configura `text/event-stream` y encabezados para evitar buffering incompatible; no necesitas construir manualmente el framing. `data` multilineal produce una línea `data:` por línea. `event` e `id` rechazan saltos de línea; `retry` requiere entero no negativo. `comment` permite un comentario/keepalive.

Un `id` identifica un evento; este módulo no guarda eventos ni reconstruye automáticamente el historial al reconectar. Si necesitas reanudación, conserva una secuencia en un servicio durable y valida el cursor recibido. No confundas `retry` con un reintento del productor en el servidor.

## Cancelación y cierre

La lectura es perezosa y se ajusta al ritmo de envío. Usa `try/finally` en productores que abren cursores, archivos o suscripciones. Las pruebas de los adaptadores cubren desconexión, cancelación y cierre de iteradores. No absorbas `CancelledError` y dejes el productor ejecutándose. Si el recurso tiene `aclose()`, su limpieza debe completarse antes de liberar el scope.

`HTTP_MONITOR_DISCONNECTS` controla monitoreo adicional para solicitudes HTTP ordinarias; SSE/WebSocket y políticas de endpoint pueden tener mecanismos propios. Verifica el adapter utilizado y la configuración de tu despliegue. Un proxy puede seguir agrupando salida aun cuando la aplicación entregue chunks; prueba el flujo completo.

Los errores previos al envío pueden convertirse en una respuesta normal. Tras enviar encabezados, comunica un error mediante el protocolo del stream o termina la conexión; no prometas cambiar a un JSON 500. El trabajo de fondo no debe depender de mantener objetos del request después de su limpieza.

Evidencia: [SSE](../../sse.py), [respuestas](../../responses.py), [streams](../../adapters/response/streams.py). Pruebas: [SSE](../../../../tests/http/test_sse.py), [ciclo SSE](../../../../tests/http/adapters/test_sse_lifecycle.py), [kernel SSE](../../../../tests/http/test_sse_kernel.py). Para bidireccionalidad consulta [WebSocket](websockets.md).
