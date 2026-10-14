# Elegir almacenamiento y entender concurrencia

Selecciona `SESSION_DRIVER` según el alcance de tus procesos y la disponibilidad necesaria. Todos los stores intercambian `SessionRecord`, que contiene identificador, datos y expiración UTC. La cookie no contiene el payload.

| Driver | Cuándo usarlo | Límite operativo |
|---|---|---|
| `memory` | Pruebas y desarrollo de un proceso. | Datos y revocaciones no se comparten entre workers; se pierden al reiniciar. |
| `file` | Persistencia en un filesystem local compartido apropiado. | JSON serializable, permisos de escritura y capacidad de temporales; comprobar semántica de locks en filesystem remoto. |
| `cache` | Reutilizar una caché configurada con TTL y reemplazo atómico. | Garantías y disponibilidad dependen del backend. |
| `database` | Compartir registros entre workers mediante una base configurada. | Tabla dedicada y permisos de esquema cuando se crea de forma perezosa. |

`SESSION_FILES` usa `storage/framework/sessions` bajo la raíz de aplicación. `SESSION_CACHE_STORE` elige repositorio de caché; `SESSION_DB_CONNECTION` y `SESSION_DB_TABLE` eligen conexión/tabla (por defecto `sessions`). No cambies driver o formato suponiendo migración automática de registros existentes.

## Un store aislado para comprobar el contrato

```python
import asyncio
from datetime import UTC, datetime, timedelta
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.memory import MemorySessionStore

async def example():
    store = MemorySessionStore()
    record = SessionRecord(id="docs-example", data={"count": 1},
                           expires_at=datetime.now(UTC) + timedelta(minutes=5))
    await store.write(record)
    loaded = await store.read(record.id)
    assert loaded is not None and loaded.data == {"count": 1}
    assert await store.delete(record.id)
    assert not await store.update(record)

asyncio.run(example())
```

El ID del ejemplo pertenece a la API de store. El manager valida IDs de cookies antes de enviarlos al backend; no utilices este ejemplo para fijar un ID elegido por un cliente.

## Mantener revocaciones ante carreras

`ISessionStore` define `read`, `write`, `update`, `delete` y `gc`, todos asíncronos. `write` crea/persiste el registro; `update` debe reemplazar únicamente un registro existente y vivo y devolver `False` si ya no puede hacerlo. No implementes `update` como un upsert incondicional: una petición atrasada podría recrear una sesión borrada por logout.

La rotación elimina el ID anterior antes de guardar el nuevo. Las actualizaciones condicionales preservan revocación, pero no aportan un merge de datos de negocio entre dos peticiones que modifican simultáneamente una sesión todavía válida. Evita acumular contadores críticos o transacciones financieras en el payload de sesión; usa almacenamiento de dominio con su control de concurrencia.

## I/O y limpieza

File escribe JSON compacto mediante reemplazo atómico y locks de bandas acotadas. Cache delega expiración al TTL del backend; database realiza updates condicionales y crea su estructura al necesitarla. `gc()` proporciona recolección de expirados en stores que la requieren; no supongas que cualquier backend elimina todos los archivos inmediatamente al expirar.

Para un store propio implementa [ISessionStore](../../contracts/store.py), conserva copias independientes cuando corresponda y verifica expiración, fallo de update tras delete, corrupción y errores de I/O. La selección del manager está integrada para los cuatro drivers existentes: incorporar otro requiere integración de servicios propia; añadir una cadena arbitraria a `SESSION_DRIVER` no registra una clase.

Evidencia: [manager](../../manager.py), [memory](../../stores/memory.py), [file](../../stores/file.py), [cache](../../stores/cache.py), [database](../../stores/database.py). Pruebas: [memory](../../../../tests/session/stores/test_memory.py), [file](../../../../tests/session/stores/test_file.py), [database](../../../../tests/session/stores/test_database.py), [cache](../../../../tests/session/stores/test_cache.py).
