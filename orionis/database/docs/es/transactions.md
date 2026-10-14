# Transacciones y concurrencia

Una transacción mantiene juntas operaciones que deben confirmarse o descartarse como una unidad. Usa un único nombre de conexión durante esa unidad. Orionis no implementa una transacción distribuida entre conexiones.

## Confirmación y reversión automática

El contexto asíncrono confirma cuando el bloque termina normalmente y revierte si escapa una excepción. Este programa comprueba que una operación interior puede fallar sin perder la operación exterior:

```python
import asyncio
from orionis.database import Connection


async def main() -> None:
    db = Connection("tx", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE events (name TEXT NOT NULL)")
        async with db.transaction():
            await db.execute("INSERT INTO events VALUES (:name)", {"name": "outer"})
            try:
                async with db.transaction():
                    await db.execute(
                        "INSERT INTO events VALUES (:name)", {"name": "inner"}
                    )
                    raise ValueError("discard inner work")
            except ValueError:
                pass
        assert await db.select("SELECT name FROM events") == [{"name": "outer"}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

En una aplicación, la forma equivalente es `async with DB.transaction():` o `async with DB.transaction("reporting"):`. La facade usa `beginTransaction()`, `commit()` y `rollback()` para control manual; la conexión directa usa `begin()`, `commit()` y `rollback()`. Prefiere el contexto: el control manual debe manejar fallos y cancelación en todas las rutas. Confirmar o revertir sin transacción activa produce `TransactionException`.

## Anidamiento y propiedad de tareas

El primer nivel abre una conexión dedicada y una transacción raíz. Los siguientes niveles crean savepoints, salvo Redshift, donde el anidamiento se rechaza. Cada `commit` o `rollback` termina solamente el nivel interior.

El estado pertenece a la tarea de asyncio que abrió la transacción. Una tarea hija hereda contexto, pero no es propietaria de la transacción: Orionis rechaza su uso con `TransactionException`. Ejecuta las consultas transaccionales secuencialmente en la tarea propietaria; no uses `asyncio.gather()` o `create_task()` dentro del bloque para compartir esa conexión. Fuera de transacción, consultas independientes pueden usar conexiones distintas del pool.

Esto también importa para [paginación](../../../orm/docs/es/querying.md): el ORM hace recuento y lectura secuencialmente dentro de una transacción y puede hacerlos concurrentemente fuera de ella.

## Cancelación y resultados inciertos

Las operaciones de control de transacción esperan a que el driver termine antes de propagar la cancelación. Si ya se solicitó `COMMIT`, los cambios pueden quedar persistidos aunque el llamador reciba `CancelledError`. Cancelar no equivale a demostrar rollback. La espera para adquirir una conexión del pool sigue siendo cancelable.

La implementación drena operaciones y limpia/invalida conexiones interrumpidas cuando corresponde, también con el puente de threads de Redshift. No promete abortar instantáneamente una consulta en el servidor. Si una respuesta de negocio queda incierta después de una confirmación, consulta por una identidad estable o aplica idempotencia antes de reintentar.

## Límites prácticos

Mantén los bloques breves. Evita peticiones HTTP o correo dentro de la transacción: prolongan la retención de recursos y no se revierten con el SQL. Si necesitas actualizar datos y enviar un job, estudia el backend de [colas](../../../queues/docs/es/drivers-and-configuration.md): una cola database participa en la transacción de su conexión, Redis no comparte la transacción SQL. No existe aquí una API general `afterCommit` que convierta ambos sistemas en una operación atómica.

DDL y savepoints dependen del motor. Que el migrador abra una transacción no convierte el DDL de todos los servidores en reversible. Prueba tanto la ruta de éxito como la de fallo en el backend elegido antes de usar una migración en producción.
