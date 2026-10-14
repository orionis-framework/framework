# Colas y jobs

Las colas separan la solicitud de trabajo de su ejecución. Un `BaseJob` declara estado serializable y un `handle` async; `Queue.dispatch()` crea un envío diferido que solo se presenta al backend al esperarlo. Los drivers incluidos son `sync`, `database` y `redis`.

1. [Escribir y enviar jobs](jobs-and-dispatch.md): estado permitido, DI, identidad de clases y envío de una sola vez.
2. [Elegir y configurar un backend](drivers-and-configuration.md): persistencia, conexiones, tablas, Redis y transacciones.
3. [Workers, reintentos y fallos](workers-and-failures.md): leases, concurrencia, timeout, backoff y recuperación.

Para trabajo durable elige database o Redis y opera un worker separado. `sync`, predeterminado, ejecuta dentro del envío y no conserva trabajo para otro proceso. La durabilidad del mensaje no garantiza que un efecto externo ocurra una sola vez: diseña jobs idempotentes.

Las facades necesitan una aplicación [inicializada](../../../foundation/docs/es/README.md). Python 3.14+, msgspec y Redis son dependencias declaradas; el backend database usa [Database](../../../database/docs/es/README.md).
