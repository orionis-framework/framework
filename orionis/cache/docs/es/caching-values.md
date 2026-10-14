# Guardar y regenerar datos

Una caché guarda datos regenerables para evitar repetir consultas o cálculos. Diseña primero la clave, el tiempo de vida y la invalidación: ningún backend sustituye la fuente persistente de verdad.

## Requisitos

- Python 3.14 o posterior.
- `aiocache[redis,memcached]>=0.12.3`, instalado por Orionis.
- Servicios Redis o Memcached cuando se seleccionen esos stores.
- Una conexión de base de datos Orionis configurada para el store database; bases distintas de SQLite pueden necesitar el extra correspondiente.
- Un directorio escribible para el store file y para `FileBasedCache`.

## Inicio rápido

Este ejemplo independiente usa el backend de memoria mediante la API pública del repositorio:

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build(), prefix="docs")
    await cache.set("greeting", {"message": "hello"}, ttl=30)
    print(await cache.get("greeting"))


asyncio.run(main())  # {'message': 'hello'}
```

La clave física es `docs:greeting`; quienes llaman siguen usando el nombre sin prefijo.

## Diseñar claves e invalidación

Incluye en la clave todos los valores que cambian el resultado: entidad, tenant, idioma y versión del formato cuando corresponda. `cache.prefix` separa nombres, pero no aplica autorización. Una clave predecible no convierte un dato privado en público; verifica el acceso antes de recuperar o devolver contenido.

`remember(key, ttl, resolver)` implementa cache-aside: si falta, calcula y guarda. El resolver recibe cero argumentos. Los resolvers síncronos se invocan directamente en el loop; si realizan I/O bloqueante, usa una función async que delegue ese trabajo a un executor. El método guarda también `None`, por lo que un resultado negativo se mantiene durante su TTL.

Después de cambiar la fuente de datos, confirma la escritura persistente y elimina las claves afectadas con `delete()`, o utiliza un TTL que admita la antigüedad resultante. Orionis no deduce dependencias entre claves y modelos ni invalida automáticamente. Evita `clear()` para invalidar un solo usuario: vacía el backend completo incluso si el repositorio tiene prefijo.

Si una lectura de caché falla, decide en la aplicación si debes regenerar desde la fuente o abortar. El repositorio propaga errores de red y serialización; no contiene un fallback automático a memory. Para información que no puede perderse, almacena primero en tu base de datos.

### Operaciones con un significado preciso

`add()` y `replace()` condicionan la escritura a ausencia o existencia. `pull()` realiza lectura y borrado separados; dos consumidores podrían recuperar el mismo valor. `getMany()` devuelve un dict con las claves solicitadas y valores `None` para ausencias. `setMany()` no implica una transacción común a todos los backends. Los contadores aceptan deltas enteros; el comportamiento de una clave ausente o de un valor no numérico depende del backend.


### Manager, repositorio y backend

`CacheManager` resuelve configuración y posee instancias de repositorio. `CacheRepository` normaliza la API y añade prefijos. Un backend realiza las primitivas específicas del almacenamiento. Las llamadas directas al manager se delegan al repositorio predeterminado.

### Resolución cache-aside

`remember(key, ttl, resolver)` lee con un sentinel privado, por lo que un `None` almacenado cuenta como hit. En un miss invoca un resolver sync o async sin argumentos, guarda el resultado y lo devuelve. No agrupa misses concurrentes; usa `lock()` alrededor de regeneración costosa cuando sea necesario.

### Almacenar un resultado de resolver, incluido `None`

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build())
    calls = 0

    async def resolve() -> None:
        nonlocal calls
        calls += 1
        return None

    await cache.remember("nullable", 60, resolve)
    await cache.remember("nullable", 60, resolve)
    print(calls)  # 1


asyncio.run(main())
```

El sentinel evita tratar el `None` almacenado como otro miss.

### Usar add atómico y pull

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build())
    print(await cache.add("ticket", "A"))  # True
    print(await cache.add("ticket", "B"))  # False
    print(await cache.pull("ticket"))       # A
    print(await cache.has("ticket"))        # False


asyncio.run(main())
```

`add` conserva el valor original en conflicto; `pull` lo elimina después de leer.

### `CacheRepository`

```text
CacheRepository(backend: Any, prefix: str = "")
```

| Método | Comportamiento |
|---|---|
| `get(key)` / `has(key)` | Lee un valor o comprueba una entrada viva. Un `get` ausente devuelve `None`. |
| `set(key, value, ttl=None)` | Guarda o sobrescribe. TTL está en segundos. |
| `replace(key, value, ttl=None)` | Reemplaza atómicamente solo una entrada viva existente. |
| `delete(key)` / `clear()` | Elimina una entrada o vacía el backend seleccionado. |
| `getMany(keys)` | Devuelve un mapping que conserva las claves pedidas sin prefijo. |
| `setMany(values, ttl=None)` | Guarda un mapping con TTL compartido. |
| `remember(key, ttl, resolver)` | Devuelve caché o calcula/guarda un resultado sync o async. |
| `rememberForever(key, resolver)` | `remember` sin expiración. |
| `pull(key)` | Lee y después elimina; ausente devuelve `None`. |
| `add(key, value, ttl=None)` | Guarda atómicamente solo si falta; conflictos devuelven `False`. |
| `increment(key, amount=1)` / `decrement(...)` | Aplica deltas enteros y devuelve el nuevo valor. |
| `lock(key, timeout=None)` | Devuelve un context manager async para la clave prefijada. |

Pueden propagarse errores del backend o serialización. `replace` lanza `CacheStoreException` si un backend personalizado no tiene reemplazo atómico.

---

[Índice](README.md) · [orm](../../../orm/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)
