# Facades, fechas y utilidades del runtime

## Conceptos principales

### Fachadas

Una fachada es un proxy a nivel de clase hacia un objeto resuelto por el contenedor de servicios de Orionis. Las importaciones son diferidas, por lo que importar `orionis.support.facades` no carga ansiosamente todos los subsistemas. Las implementaciones de runtime son deliberadamente pequeñas, mientras los archivos `.pyi` adyacentes exponen la API delegada a verificadores de tipos y editores.

La mayoría de fachadas operan en todo el proceso. `Session` está vinculada a un ámbito, por lo que su resolución sigue el ámbito activo de petición o ejecución. No conserves servicios de petición resueltos entre ámbitos.

### Valores auxiliares

`Collection` aporta transformaciones fluidas alrededor de una lista. La mayoría de consultas devuelve una colección nueva; métodos explícitamente mutables como `push`, `put`, `forget`, `merge` y `transform` actualizan el objeto actual. `DotDict` permite acceso recursivo por atributos, `StdClass` almacena atributos dinámicos validados, `Stringable` es una subclase inmutable de `str` con operaciones fluidas, y `MISSING` diferencia un valor omitido de `None`.

### Entidades y estructuras

`BaseEntity` está pensado para combinarse con `@dataclass`. Serializa dataclasses anidados y campos enum mediante `toDict()` y describe tipos, valores predeterminados y metadatos mediante `getFields()`. `FreezeThaw` convierte recursivamente diccionarios en proxies de mapeo de solo lectura y secuencias en tuplas, preservando referencias repetidas dentro del grafo recorrido.

### Auxiliares transversales

`Singleton` implementa una instancia por clase concreta con una ruta de inicialización protegida por bloqueo. `Final` impide crear subclases. `PerformanceCounter` mide intervalos síncronos o asíncronos. `Workers` elige una cantidad de procesos a partir de límites en caché de CPU lógica y memoria total. `Parser.exception()` crea una representación estructurada y cacheada de una excepción. `Inspire` devuelve una cita elegida criptográficamente.

## API pública

### Fachadas

Importa las fachadas desde `orionis.support.facades`:

| Fachada | Área de servicio |
| --- | --- |
| `Application` | Contenedor y ciclo de vida de la aplicación. |
| `Auth` | Gestor de autenticación. |
| `Cache` | Almacenes y operaciones de caché. |
| `Catch` | Servicio de reporte de excepciones. |
| `Crypt` | Cifrado y descifrado. |
| `DateTime` | Utilidades autónomas de fecha, zona horaria, duración e intervalo. |
| `DB` | Constructor de consultas de base de datos. |
| `Hash` | Hash de contraseñas y valores. |
| `Lang` | Traducción. |
| `Log` | Registro estructurado. |
| `Mail` | Construcción y entrega de correo. |
| `Mcp` | Registro de servidores MCP y notificaciones. |
| `Queue` | Despacho, conexiones, workers y trabajos fallidos de colas. |
| `Reactor` | Ejecución de comandos de consola. |
| `Realtime` | Clientes de hubs y conexiones en tiempo real. |
| `Route` | Enrutamiento HTTP, WebSocket, MCP y de vistas. |
| `Schedule` | Comandos y callbacks programados. |
| `Schema` | Operaciones de esquema de base de datos. |
| `Session` | Estado de sesión local al ámbito. |
| `Storage` | Discos configurados del sistema de archivos. |
| `Test` | Motor de pruebas del framework. |
| `View` | Fábrica y renderizado de vistas. |

Salvo `DateTime`, estas clases obtienen su destino del contenedor. Consulta la documentación del módulo propietario para el contrato delegado completo.

### Tipos y auxiliares

- `Collection(items=None)`: selección, mapeo, agrupación, agregación, paginación, serialización y protocolos de lista fluidos.
- `DotDict(mapping)`: acceso por clave y atributo; `export()` restaura diccionarios recursivamente y `copy()` copia mapeos anidados.
- `StdClass(**kwargs)`: atributos dinámicos que rechazan nombres reservados o dunder; admite `fromDict`, `toDict`, `update` y `remove`.
- `Stringable(value)`: envoltorio inmutable y fluido de texto con utilidades de formato, coincidencia, reemplazo, codificación, hash, análisis, truncado y validación.
- `MISSING`: centinela falso cuya representación es `MISSING`.
- `BaseEntity`: `toDict()` y `getFields()` para entidades dataclass.
- `FreezeThaw.freeze()` / `thaw()`: conversiones recursivas inmutables/mutables.
- `PerformanceCounter`: `start`/`stop`, `astart`/`astop`, gestores de contexto y conversiones de duración.
- `Workers.setRamPerWorker()` / `calculate()`: cálculo de capacidad de procesos.
- `Parser.exception(error)`: produce un `ExceptionParser`; invoca `toDict()` para `error_type`, `error_message`, `error_code` y `stack_trace`.
- `Inspire.random()`: devuelve un mapeo `{"quote": ..., "author": ...}`.
- `Final` y `Singleton`: metaclases para clases finales y singleton.

## Ejemplos

### Medir una operación

```python
from orionis.support.performance import PerformanceCounter

with PerformanceCounter() as counter:
    total = sum(range(100))

assert total == 4950
assert counter.getSeconds() >= 0
assert counter.getMilliseconds() >= 0
```

### Trabajar con fechas sin inicializar el contenedor

```python
from orionis.support.facades import DateTime

instant = DateTime.parse("2026-10-06T12:30:00Z")
later = DateTime.addDays(instant, 2)

assert instant.timezone_name == "UTC"
assert later.to_date_string() == "2026-10-08"
assert DateTime.diffInDays(instant, later) == 2
```

### Invocar una fachada respaldada por el contenedor

```python
from orionis.support.facades import Cache, Log, Storage

# Run after the Orionis application has booted and bound these services.
async def completed_import() -> None:
    Log.info("Import completed")
    await Cache.set("imports:last", "customers.csv", ttl=300)
    await Storage.disk("local").put("imports/customers.txt", b"done")
```

## Configuración

Los destinos de las fachadas se configuran en sus módulos propietarios y se resuelven desde el contenedor Orionis actual. `DateTime` recibe la zona horaria y el idioma de la aplicación mediante su cargador interno durante el arranque; los argumentos `tz` explícitos sustituyen ese valor para operaciones individuales.

`Workers` usa por defecto 0,5 GiB por worker. `setRamPerWorker()` cambia un presupuesto de clase para todo el proceso. `Inspire` admite una lista personalizada de mapeos con las claves obligatorias `quote` y `author`. Los demás tipos auxiliares no requieren configuración global.

## Integración con Orionis

Usa fachadas en límites de aplicación —controladores, comandos, trabajos, listeners y proveedores— donde resulte útil acceder concisamente a un servicio configurado. Prefiere inyección por constructor dentro de servicios de dominio reutilizables cuando importen las dependencias explícitas y las pruebas aisladas.

El paquete diferido de fachadas evita importar todos los subsistemas al arrancar. Los stubs de tipos conservan la finalización estática alineada con los contratos reales de gestores. `BaseEntity`, `Collection` y `Stringable` también se usan en Orionis para ofrecer serialización y operaciones fluidas de valores coherentes.

## Errores y casos límite

- Una fachada respaldada por servicios falla si su binding no está disponible o no existe un ámbito requerido activo.
- `DotDict.missing` devuelve `None`; usa comprobación de pertenencia cuando `None` sea un valor almacenado significativo.
- `StdClass` rechaza nombres dunder y nombres que colisionan con su API de clase.
- `Collection.chunk()` y `forPage()` rechazan tamaños no positivos; las operaciones con callbacks exigen objetos invocables.
- `FreezeThaw` solo transforma diccionarios, listas, tuplas y proxies de mapeo. Los objetos almacenados dentro no se copian profundamente.
- `PerformanceCounter` impide leer antes de completar una medición y mezclar métodos de inicio/parada síncronos y asíncronos.
- `Final` rechaza la herencia al crear la clase. `Singleton` ignora argumentos del constructor después de existir la primera instancia.
- Zonas horarias inválidas y entradas de fecha incompatibles producen errores de validación de `DateTime`/`pendulum`.
- `Workers.setRamPerWorker()` exige un valor finito, positivo y suficiente para representar al menos un byte.

## Rendimiento y concurrencia

Las importaciones de fachadas y sus exportaciones raíz son diferidas y cacheadas. `BaseEntity` cachea metadatos normalizados de campos por clase de entidad. `ExceptionParser` analiza una vez y devuelve su diccionario cacheado en llamadas posteriores. `DateTime` cachea instancias de `ZoneInfo` hasta que cambia su zona horaria.

`Singleton` protege la primera construcción con un `threading.Lock` por clase; su método asíncrono usa la misma sección crítica breve y no realiza E/S bloqueante. `FreezeThaw` usa recorrido iterativo para evitar límites de recursión. `Workers` cachea CPU y RAM total al importar el módulo, por lo que los cálculos posteriores usan aritmética entera de tiempo constante.

`Collection` y los auxiliares mutables no están sincronizados. No mutues una misma instancia de forma concurrente sin coordinación en la aplicación.

## Compatibilidad

El módulo sigue el requisito del repositorio de Python 3.14+. Los nombres públicos usan la convención camelCase de Orionis. Los archivos `.pyi` de fachadas forman parte del contrato para desarrolladores y deben permanecer sincronizados con sus interfaces de runtime. Los tokens de formato enviados a `DateTime.fromFormat()` siguen las convenciones de Pendulum, distintas de las de `datetime.strptime()`.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| `entities/` | Serialización y metadatos de campos de `BaseEntity` para dataclasses. |
| `facades/` | Proxies diferidos de servicios y contratos públicos `.pyi`. |
| `formatter/` | Conversión de excepciones a diccionarios. |
| `inspirational/` | Proveedor y catálogo de citas. |
| `patterns/final/` | Metaclase `Final`. |
| `patterns/singleton/` | Metaclase `Singleton` segura entre hilos. |
| `performance/` | `PerformanceCounter` síncrono/asíncrono. |
| `structures/` | Conversiones recursivas `FreezeThaw`. |
| `system/` | Cálculo de workers según CPU/RAM. |
| `types/` | `Collection`, `DotDict`, `StdClass`, `Stringable` y `MISSING`. |

## Fuentes y siguientes pasos

[__init__.py](../../facades/__init__.py) · [datetime.py](../../facades/datetime.py) · [counter.py](../../performance/counter.py) · [workers.py](../../system/workers.py)

[Volver al índice del módulo](README.md).
