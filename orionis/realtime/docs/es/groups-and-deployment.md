# Grupos, broadcasts y despliegue

Los grupos seleccionan conexiones de un Hub, por ejemplo participantes de una sala. No son roles de seguridad: comprueba que la identidad pueda acceder a la sala antes de incorporarla. Las membresías se eliminan al desconectar y no constituyen una suscripción durable.

```python
from orionis.realtime import Hub, remote

class RoomHub(Hub):
    @remote
    async def join(self, room: str) -> None:
        if self.context.user is None:
            from orionis.realtime.errors import RPCError
            raise RPCError("unauthenticated", "Sign in first")
        await self.groups.join(room)
        await self.clients.group(room).send("joined", self.context.connection_id)
```

El ejemplo comprueba identidad, pero una sala privada necesita además una autorización de dominio para ese nombre. No admitas un nombre controlado por el cliente como prueba de pertenencia. `groups.leave(name)` permite salir. Identificadores y grupos se validan para acotar tamaño y contenido.

## Seleccionar destinatarios

`clients.all`, `.caller` y `.others` son propiedades; `.client(id)`, `.clients(ids)` y `.group(name)` son métodos. Todos los targets permiten `await target.send(event, *args)`. `.caller` y `.others` requieren una invocación con llamador. Para un evento desde un controlador o job usa `Realtime.hub(RoomHub).all.send(...)`, importando Realtime de `orionis.support.facades`; esa selección no tiene caller.

```python
import asyncio
from orionis.realtime import ConnectionManager
from orionis.realtime.config import RealtimeConfig
from orionis.realtime import Hub

class EmptyHub(Hub):
    pass

async def example():
    manager = ConnectionManager(RealtimeConfig())
    result = await manager.hub(EmptyHub).all.send("refresh", {"version": 1})
    assert (result.sent, result.failed) == (0, 0)

asyncio.run(example())
```

`BroadcastResult.sent` cuenta entregas al transporte y `failed` destinatarios fallidos; no confirma ejecución de código cliente. El broadcast toma snapshot de IDs y vuelve a comprobar disponibilidad antes de escribir. Desconexiones durante el envío pueden figurar como fallos.

## Presupuestos de ejecución

| Variable | Predeterminado |
|---|---:|
| `REALTIME_MAX_MESSAGE_SIZE` | 1 MiB |
| `REALTIME_MAX_CONCURRENT_INVOCATIONS` | 16 por conexión |
| `REALTIME_MAX_PENDING_CLIENT_INVOCATIONS` | 32 por conexión |
| `REALTIME_INVOCATION_TIMEOUT` | 30 segundos, scalar |
| `REALTIME_CLIENT_RESULT_TIMEOUT` | 30 segundos |
| `REALTIME_BROADCAST_CONCURRENCY` | 32 entregas concurrentes |
| `REALTIME_MAX_GROUPS_PER_CONNECTION` | 64 |

Los límites son enteros positivos y los timeouts finitos positivos. `config/realtime.py` construye `RealtimeConfig`; el provider lo registra como configuración inmutable. Combínalos con límites WebSocket HTTP de mensajes y conexiones. No asumas que elevar el límite Realtime eleva automáticamente el del transporte.

## Workers, orden y extensiones

`ConnectionManager` y grupos son locales al worker. Dos procesos no ven conexiones del otro; reiniciar pierde registro/membresías. Para difusión entre workers necesitas un backplane propio y una implementación compatible de `IConnectionManager`. No se entrega Redis pub/sub o almacenamiento offline automáticamente por configurar Redis en otro módulo.

Cada conexión serializa escrituras mediante lock y aplica backpressure; una escritura fallida cierra conexión y cancela su owner para evitar adelantamientos posteriores. El broadcast acota fan-out y codifica una vez por codec. Accede al manager en el event loop de la aplicación; no está diseñado como registry thread-safe global.

La reflexión remota se cachea para hasta 1024 clases Hub. Instancias y scopes se mantienen por invocación. No retengas recursos scoped en tareas que sobrevivan a la conexión; controla cancelación, join y cierre de cualquier tarea propia.

Evidencia: [clients](../../clients.py), [groups](../../groups.py), [manager](../../manager.py), [contrato](../../contracts/manager.py), [config](../../../../config/realtime.py). Pruebas: [manager](../../../../tests/realtime/test_manager.py), [conexiones](../../../../tests/realtime/test_connection.py), [metadata](../../../../tests/realtime/test_metadata.py). Revisa [WebSocket](../../../http/docs/es/websockets.md) para límites del handshake.
