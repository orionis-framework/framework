# Protocolo, streams y resultados bidireccionales

El protocolo v1 utiliza envelopes con campo `type`. El cliente debe esperar `ready`, correlacionar IDs y distinguir respuestas normales de streams y eventos. JSON usa texto WebSocket; MessagePack usa bytes. Enviar el tipo de frame equivocado es un error de protocolo.

## Una llamada y una cancelación

```json
{"type":"invoke","id":"call-1","target":"sum","args":[2,3],"kwargs":{}}
```

Una respuesta scalar llega como `completion` con el mismo ID y resultado o error. Para cancelar una llamada activa:

```json
{"type":"cancel","id":"call-1"}
```

IDs de hasta 128 caracteres ASCII imprimibles no pueden contener espacios. La cantidad de args y kwargs está acotada a 64 de cada uno. No reutilices un ID mientras su operación siga activa. Una completion de cliente debe incluir exactamente resultado o error; un resultado `null` es válido. Completions desconocidas o duplicadas no se retienen.

## Producir una secuencia

```python
from collections.abc import AsyncIterator
from orionis.realtime import Hub, remote
from orionis.realtime.metadata import compile_hub

class FeedHub(Hub):
    @remote
    async def updates(self, count: int) -> AsyncIterator[int]:
        for value in range(count):
            yield value

assert compile_hub(FeedHub)["updates"].is_stream
```

El runtime entrega `stream_item` y después `stream_complete`. La iteración sigue el ritmo del socket. Usa `try/finally` en generadores que abren recursos; cancelación/desconexión debe cerrar el iterador antes de liberar el scope. Los streams no tienen timeout predeterminado de vida; un `timeout` explícito en invoke sí limita la operación. Las llamadas escalares usan `REALTIME_INVOCATION_TIMEOUT` si no se especifica otro.

## Pedir un resultado al cliente

Dentro del hub, `await self.clients.caller.invoke("confirm", payload, timeout=5.0)` envía una invocación y espera su completion correlacionada; `payload` debe ser un valor serializable preparado por tu método. También funciona sobre `clients.client(id)`. Un target múltiple no admite `invoke`: no hay un único resultado a correlacionar. Para eventos sin espera utiliza `send`.

El lector de conexión sigue disponible mientras espera resultados, por lo que las respuestas pueden llegar fuera de orden. Las invocaciones pendientes tienen capacidad y plazo acotados. Un error del cliente produce `ClientInvocationError` saneado; no incorpora texto arbitrario del peer en diagnósticos internos.

## Cierre y compatibilidad

Un protocolo inválido cierra con 1002, frame incorrecto con 1003 y tamaño excesivo con 1009. Ping/pong de aplicación están disponibles; no equivalen a persistencia ni a una tarea automática de heartbeat. Escribe clientes que liberen callbacks pendientes al desconectar y reconcilien su estado al reconectar: no hay replay automático.

Evidencia: [protocolo](../../protocol.py), [conexión](../../connection.py), [runtime](../../runtime.py). Pruebas: [wire](../../../../tests/realtime/test_protocol.py), [correlación](../../../../tests/realtime/test_connection.py), [streams](../../../../tests/realtime/test_runtime.py). Continúa con [grupos y despliegue](groups-and-deployment.md).
