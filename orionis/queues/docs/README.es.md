# orionis.queues

> Referencia de API derivada de la implementación actual.

## Tabla de contenido

- Requisitos
- Resumen funcional
- Estructura del módulo
- Referencia de API
- Ejemplos de uso
- Características de diseño
- Rendimiento y concurrencia
- Notas de compatibilidad
- Verificación y limitaciones

## Requisitos

Python 3.14 o superior, como declara pyproject.toml.

## Resumen funcional

El inicializador de orionis.queues expone 4 símbolos públicos. Esta referencia usa __all__, las rutas de exportación y los archivos fuente actuales como evidencia.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| ../__init__.py | Define las exportaciones del paquete. |
| orionis.queues/ | Implementaciones y subpaquetes de esas exportaciones. |

## Referencia de API

| Símbolo | Importación verificada | Fuente | Declaración | Comportamiento observado |
| --- | --- | --- | --- | --- |
| BaseJob | from orionis.queues import BaseJob | [job.py](../job.py) | BaseJob | Declare serializable job fields and asynchronous service dependencies. Attributes ---------- tries : int / None Maximum reservations, or the configured worker default. timeout : float / None Cooperative execution timeout, or the configured worker default. backoff : tuple[float, ...] / None Delay after each failed attempt, or the configured worker default. |
| BaseJob.retryUntil | from orionis.queues import BaseJob | [job.py](../job.py) | def retryUntil(self) -> float / None | Return an optional absolute retry deadline. Returns ------- float / None Epoch seconds from DateTime, or no deadline. |
| JobContext | from orionis.queues import JobContext | [context.py](../context.py) | JobContext | Expose the current reservation and explicit lifecycle operations. |
| JobContext.id | from orionis.queues import JobContext | [context.py](../context.py) | def id(self) -> str | Return the immutable job identifier. Returns ------- str Dispatch identifier. |
| JobContext.attempts | from orionis.queues import JobContext | [context.py](../context.py) | def attempts(self) -> int | Return the number of reservations including this execution. Returns ------- int One-based attempt count. |
| JobContext.queue | from orionis.queues import JobContext | [context.py](../context.py) | def queue(self) -> str | Return the logical queue name. Returns ------- str Channel containing the job. |
| JobContext.connection | from orionis.queues import JobContext | [context.py](../context.py) | def connection(self) -> str | Return the logical backend connection name. Returns ------- str Configured connection name. |
| JobContext.finished | from orionis.queues import JobContext | [context.py](../context.py) | def finished(self) -> bool | Report whether an explicit lifecycle operation completed. Returns ------- bool Whether automatic worker acknowledgement must be skipped. |
| JobContext.failure | from orionis.queues import JobContext | [context.py](../context.py) | def failure(self) -> Exception / None | Return an explicitly reported terminal exception. Returns ------- Exception / None Error passed to ``fail``. |
| JobContext.release | from orionis.queues import JobContext | [context.py](../context.py) | async def release(self, delay: float) -> None | Release the reservation for another attempt. Parameters ---------- delay : float, optional Nonnegative delay in seconds. Returns ------- None Complete the documented operation without returning a value. Raises ------ QueueConfigurationError If the delay is invalid. QueueLeaseError If the reservation is no longer owned by this execution. |
| JobContext.delete | from orionis.queues import JobContext | [context.py](../context.py) | async def delete(self) -> None | Acknowledge the job and remove its reservation. Returns ------- None Complete the documented operation without returning a value. Raises ------ QueueLeaseError If the reservation is no longer owned by this execution. |
| JobContext.fail | from orionis.queues import JobContext | [context.py](../context.py) | async def fail(self, exception: Exception) -> None | Persist a terminal error and acknowledge the reservation. Parameters ---------- exception : Exception Original application exception. Returns ------- None Complete the documented operation without returning a value. Raises ------ QueueLeaseError If the reservation is no longer owned by this execution. |
| JobEnvelope | from orionis.queues import JobEnvelope | [entities/envelope.py](../entities/envelope.py) | JobEnvelope | Carry immutable, versioned job data independently of backend state. |
| PendingDispatch | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | PendingDispatch | Defer a single dispatch until awaited and allow options before submission. |
| PendingDispatch.onConnection | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | def onConnection(self, name: str) -> PendingDispatch | Select the configured backend before submission. Parameters ---------- name : str Connection name from queue configuration. Returns ------- PendingDispatch This pending operation. |
| PendingDispatch.onQueue | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | def onQueue(self, name: str) -> PendingDispatch | Select a logical channel before submission. Parameters ---------- name : str Channel within the selected connection. Returns ------- PendingDispatch This pending operation. |
| PendingDispatch.delay | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | def delay(self, seconds: float) -> PendingDispatch | Schedule availability relative to submission time. Parameters ---------- seconds : float Finite nonnegative delay. Returns ------- PendingDispatch This pending operation. |

## Ejemplos de uso

    from orionis.queues import BaseJob

La ruta de importación coincide con la tabla de API. Estado de importación: executed successfully under Python 3.14.3.

## Características de diseño

El paquete utiliza una superficie pública explícita. Los símbolos privados no se incluyen; las declaraciones se enlazan al propietario concreto.

## Rendimiento y concurrencia

No se declara una garantía uniforme en el nivel del paquete. Inspeccione cada archivo enlazado para E/S, corutinas, cachés, bloqueos y estado compartido.

## Notas de compatibilidad

Mínimo declarado: Python 3.14. La validación usó Python 3.14.3. Los límites de dependencias están en pyproject.toml.

## Verificación y limitaciones

Se analizaron los archivos Python y se verificaron las exportaciones. Las excepciones de dependencias, callbacks, E/S o configuración pueden propagarse y no se presentan como exhaustivas.
