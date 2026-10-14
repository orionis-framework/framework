# Workers, reintentos y fallos

## Consumir trabajo durable

Arranca un worker desde la raíz de la aplicación con la misma versión de código y configuración que el productor:

```shell
python reactor queue:work database --queue high,default --concurrency 4
python reactor queue:work database --queue reports --stop-when-empty --max-jobs 100
```

Las colas se recorren en orden de prioridad; un flujo continuo en `high` puede retrasar `default`. Cada worker tiene consumidores propios hasta su concurrencia y cada ejecución recibe un scope de DI aislado. `--max-jobs` cuenta reservas procesadas, incluidos intentos fallidos y reintentos, no solamente jobs únicos completados.

`--stop-when-empty` termina cuando no hay trabajo **listo**; puede haber mensajes con delay futuro. Para servicio continuo omite esa opción y configura supervisión/reinicio externo. No existe en esta capa un supervisor distribuido integrado.

La API de servicio equivalente es:

```python
from orionis.support.facades import Queue


async def drain_reports() -> int:
    worker = await Queue.worker("database", queues=("reports",), concurrency=2)
    return await worker.run(stop_when_empty=True, max_jobs=100)
```

`worker.stop()` solicita dejar de reservar y permite terminar ejecuciones activas. Las señales del comando CLI siguen este flujo. Cancelar la ejecución interna intenta liberar reservas pendientes cuando es posible; un lease perdido no se puede confirmar. La parada no deshace efectos de negocio ya realizados.

## Reservas, timeout y recuperación

El driver reserva atómicamente durante `retry_after` y entrega un token de fencing. La finalización exige que la reserva siga perteneciendo a ese intento. Tras caída del worker y vencimiento del lease, otro consumidor puede reservar de nuevo. Ese mecanismo evita confirmar con un token obsoleto, pero no impide que un proveedor externo haya recibido ya la acción.

`timeout` es un límite cooperativo con `asyncio.timeout`, recortado por el tiempo restante del lease. Debe quedar por debajo de `retry_after`; deja margen para ACK y manejo de fallos. No detiene código Python/SDK bloqueante que no cede al event loop. Divide operaciones extensas y usa APIs async; aumentar concurrencia no arregla trabajo bloqueante.

El envelope conserva el `timeout`, número máximo de intentos, backoff y deadline seleccionados al enviar. Cambiar defaults del worker después no reescribe mensajes ya persistidos. Un job puede sobrescribir `tries`, `timeout`, `backoff` y `retryUntil()`; este último devuelve segundos epoch absolutos o `None`.

## Reintentos y decisiones explícitas

`tries=3` permite el primero y dos reintentos. Para `backoff=(1.0, 5.0)`, el primer fallo espera un segundo y los siguientes usan cinco; si se agota la secuencia se repite su último valor. El worker no reintenta fallos de payload, configuración o elegibilidad de retry como si fueran errores temporales de negocio. Un deadline vencido o agotamiento de intentos lleva a fallo terminal.

Un `handle(self, context: JobContext)` puede decidir:

| Operación async | Efecto |
|---|---|
| `await context.release(delay=5.0)` | Libera para otro intento. |
| `await context.delete()` | Confirma y elimina la reserva. |
| `await context.fail(error)` | Registra fallo terminal y confirma. |

`id`, `attempts`, `queue`, `connection`, `finished` y `failure` permiten inspección. Tras una transición completa, otra produce `QueueLeaseError`. Después de `release`, `delete` o `fail`, devuelve de `handle`: continuar puede producir efectos aunque el contexto ya terminó. Si termina normalmente sin decisión, el worker confirma automáticamente.

## Inspeccionar y recuperar fallos

```shell
python reactor queue:failed
python reactor queue:retry failure-id
python reactor queue:forget failure-id
```

Se guarda el payload original con detalles de excepción y traceback. Protege ese almacenamiento: puede contener datos de negocio sensibles. `await Queue.failed()` devuelve el repositorio, con `all()`, `find(id)` y `forget(id)` async. `await Queue.retryFailed(id)` reenvía el envelope por su conexión original y elimina el registro de fallo **después** de un push correcto; conserva la identidad del job y reinicia intentos en el backend. Un deadline original vencido impide retry; un push fallido conserva el registro.

`queue:forget` elimina evidencia del fallo sin ejecutar trabajo. `queue:clear [connection] --queue reports` elimina estados listos, retrasados **y reservados**; no es limpieza de jobs completados. Puede invalidar trabajo que aún se ejecuta.

Si falla el repositorio de fallos, el worker puede conservar una reserva sin confirmar para recuperación tras vencimiento y registra el problema. Monitoriza tanto fallos de negocio como fallos de almacenamiento. Ningún registro/ACK de cola coordina atómicamente un pago o envío externo: aplica claves de idempotencia, operaciones condicionales o reconciliación en el servicio de negocio.

## Driver sync y límites actuales

Sync ejecuta un solo intento en el envío, propaga su error y no conserva retry; también puede necesitar el repositorio SQL para un fallo terminal. No uses `.delay()` ni `context.release()` con él. No hay APIs incluidas de cadenas, batches de jobs, routing por decorador, heartbeat de lease o cancelación remota de efectos externos. Estas capacidades requieren diseño de aplicación/extensión y no deben inferirse de otros frameworks.
