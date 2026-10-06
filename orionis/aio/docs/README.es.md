# orionis.aio

> `orionis.aio` proporciona el ciclo de vida del event loop adaptado a la plataforma y puentes seguros entre callables síncronos y asíncronos de Orionis.

## Descripción general

Utiliza este módulo cuando el código deba iniciar un punto de entrada asíncrono, obtener un loop fuera de código async, ejecutar trabajo bloqueante sin ocupar el hilo del loop actual, crear una tarea con nombre o llamar una corrutina desde código síncrono. El punto de entrada público es `Loop`, importado con `from orionis.aio import Loop`.

`Loop` es una utilidad de clase; no se instancia. Selecciona una factoría de event loops una vez, conserva loops que no están en ejecución en almacenamiento local del hilo y expone operaciones explícitas para los límites habituales entre código síncrono y asíncrono. Orionis usa `Loop.execute` en la composición y los transportes de correo, y `Loop.runSync` en validación síncrona de esquemas.

## Requisitos

- Python 3.14 o posterior, según declara el proyecto.
- Una instalación normal de Orionis. No existe un extra de instalación específico para `aio`.
- En plataformas distintas de Windows, el proyecto declara `uvloop>=0.22.1`; `Loop` lo utiliza cuando se puede importar. En Windows, `uvloop` no es necesario y Orionis intenta usar `asyncio.ProactorEventLoop`.
- No se requiere iniciar la aplicación, registrar un binding en el contenedor, preparar un archivo de configuración ni disponer de un servicio externo para usar `Loop` directamente.

## Inicio rápido

Ejecuta el punto de entrada async de una aplicación y mueve un callable bloqueante al ejecutor predeterminado del loop:

```python
import time

from orionis.aio import Loop


def blocking_label(value: int) -> str:
    time.sleep(0.01)
    return f"job-{value}"


async def main() -> str:
    label = await Loop.execute(blocking_label, 7)
    return label.upper()


result = Loop.run(main())
print(result)  # JOB-7
```

`Loop.run` crea y posee el loop del punto de entrada. `Loop.execute` invoca `blocking_label` en el ejecutor predeterminado y devuelve después su resultado a `main`.

Validación: **Executed successfully** en CPython 3.14.6.

## Conceptos principales

### Loop de punto de entrada frente al loop actual

`Loop.run(coro)` está destinado a un punto de entrada síncrono donde no haya un event loop en ejecución en el hilo que llama. Dentro de código async, utiliza `await` de forma normal. `Loop.getEventLoop()` devuelve el loop activo cuando se llama desde código async; fuera de él, el método crea o reutiliza un loop abierto almacenado para el hilo actual.

### Puente de callables

`Loop.execute(func, *args, **kwargs)` acepta ambos tipos de callable. Una función corrutina se llama y espera en el loop actual. Un callable síncrono se envía al ejecutor predeterminado de ese loop. Si el callable síncrono devuelve un awaitable, el objeto devuelto se espera después en el loop actual.

### Puente síncrono de corrutinas

`Loop.runSync(coro)` bloquea deliberadamente hasta que termina la corrutina. Sin un loop activo delega en `Loop.run`. Con un loop activo en el hilo que llama, envía `Loop.run(coro)` a un `ThreadPoolExecutor` compartido de un solo worker, donde la corrutina recibe un loop separado.

### Propiedad y limpieza del loop

`Loop.eventLoopContext()` toma prestado el loop devuelto por `getEventLoop`; no lo cierra. Al salir, cuando ese loop no está en ejecución, cancela y drena todas sus tareas pendientes. Cuando se llama desde un loop ya activo, omite la limpieza para no cancelar la tarea que impulsa al llamador.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `__init__.py` | Reexporta `Loop` como único símbolo de nivel superior soportado por el paquete. |
| `loop.py` | Implementa la selección de factoría, reutilización de loops por hilo, limpieza de tareas, despacho de callables y puentes sync/async. |

## API pública

### `Loop`

Import recomendado:

```python
from orionis.aio import Loop
```

Todos los métodos públicos son estáticos o de clase y operan sobre estado compartido de la clase.

#### `getEventLoop()`

```text
Loop.getEventLoop() -> asyncio.AbstractEventLoop
```

Devuelve el loop que se está ejecutando en el hilo que llama. Si ninguno está activo, reutiliza el loop abierto almacenado para ese hilo o crea uno nuevo, lo instala con `asyncio.set_event_loop` y lo guarda en almacenamiento local del hilo. Un loop almacenado que ya esté cerrado se reemplaza. Los loops nunca se comparten entre almacenamientos locales de hilos distintos.

#### `run(coro)`

```text
Loop.run(coro: Coroutine[Any, Any, T]) -> T
```

Ejecuta un objeto corrutina nativo hasta completarlo y devuelve su valor. La selección de factoría es `uvloop.new_event_loop` cuando está disponible fuera de Windows, después `asyncio.ProactorEventLoop` en Windows cuando se expone y, por último, la factoría estándar de `asyncio`. Si existe una factoría explícita, la implementación usa `asyncio.Runner`; en caso contrario usa `asyncio.run`.

El método acepta un objeto corrutina, no una función corrutina ni un awaitable general. Devuelve `0` después de `KeyboardInterrupt`, propaga las demás excepciones de la corrutina y rechaza su uso desde un hilo que ya tenga un loop en ejecución.

#### `execute(func, /, *args, **kwargs)`

```text
await Loop.execute(func, *args, **kwargs) -> Any
```

Invoca directamente una función corrutina y la espera. Mueve cualquier otro callable al ejecutor predeterminado del loop actual mediante `run_in_executor(None, ...)`. Los argumentos y valores de retorno pasan sin alteración; si el callable ejecutado fuera del loop devuelve un awaitable, este se espera antes de devolver el resultado. Las excepciones originales atraviesan sin cambios el límite de `await`.

Este método debe llamarse dentro de un event loop activo. No utiliza el ejecutor privado de un solo worker reservado para `runSync`.

#### `eventLoopContext()`

```python
with Loop.eventLoopContext() as loop:
    assert loop is Loop.getEventLoop()
```

Entrega el resultado de `getEventLoop()`. Al salir de un loop que no está en ejecución, cancela todas sus tareas pendientes y las reúne con `return_exceptions=True`. La limpieza suprime `RuntimeError` y `asyncio.CancelledError`, incluido el caso en que el código dentro del bloque haya cerrado el loop. El contexto deja el loop abierto y reutilizable cuando puede hacerlo.

#### `isLoopRunning()`

```text
Loop.isLoopRunning() -> bool
```

Indica si un event loop se está ejecutando activamente en el hilo que llama. Tener un loop almacenado pero inactivo no hace que devuelva `True`.

#### `createTask(coro, *, name=None)`

```text
await Loop.createTask(coro, name=None) -> asyncio.Task[T]
```

Crea la tarea en el loop actual en ejecución y la devuelve sin esperar a que termine. Aunque el método en sí es async, quien llama debe conservar o esperar la tarea devuelta para observar su finalización y excepciones. El nombre opcional se reenvía a `loop.create_task`.

#### `runSync(coro)`

```text
Loop.runSync(coro: Coroutine[Any, Any, T]) -> T
```

Espera sincrónicamente una corrutina y devuelve su resultado. En un hilo sin loop en ejecución, es una llamada directa a `run`. En un hilo con un loop en ejecución, mueve la ejecución al ejecutor compartido de un worker que el módulo crea de forma diferida. Las excepciones lanzadas por la corrutina se vuelven a lanzar en el hilo que llama.

Como `runSync` bloquea el hilo que llama, debe reservarse para APIs genuinamente síncronas. Quienes llaman desde async y controlan su cadena de llamadas deben usar `await`.

## Flujos de trabajo comunes

### Iniciar una CLI o un script

Define una corrutina de nivel superior, crea el objeto corrutina y pásalo a `Loop.run`. No llames `Loop.run` desde un manejador async; se intentaría anidar event loops en un mismo hilo.

### Llamar código bloqueante desde código async

Pasa la función síncrona y sus argumentos a `await Loop.execute(...)`. El loop permanece disponible para ejecutar otras tareas mientras el ejecutor predeterminado realiza la llamada bloqueante. Las funciones corrutina pueden usar el mismo punto de entrada y se esperan directamente.

### Programar trabajo concurrente

Dentro de un loop activo, llama `await Loop.createTask(coro, name=...)` para cada corrutina. Conserva las tareas devueltas y después espéralas individualmente o con `asyncio.gather`.

### Adaptar una operación async a un contrato síncrono

Usa `Loop.runSync(coro)` únicamente en un límite síncrono que no pueda hacerse async. Si quien llama ya está en el hilo de un event loop, el puente usa su worker dedicado para no intentar ejecutar un segundo loop en ese mismo hilo. La llamada sigue bloqueando al llamador hasta completarse.

## Ejemplos

### Despachar callables sync y async mediante una sola interfaz

La misma operación maneja ambos estilos de callable y conserva los argumentos con nombre:

```python
from orionis.aio import Loop


def sync_join(*, left: str, right: str) -> str:
    return f"{left}:{right}"


async def async_join(*, left: str, right: str) -> str:
    return f"{left}/{right}"


async def main() -> tuple[str, str]:
    sync_value = await Loop.execute(sync_join, left="a", right="b")
    async_value = await Loop.execute(async_join, left="a", right="b")
    return sync_value, async_value


print(Loop.run(main()))  # ('a:b', 'a/b')
```

La función síncrona se ejecuta en el ejecutor predeterminado del loop; la función corrutina permanece en el loop del llamador.

Validación: **Executed successfully** en CPython 3.14.6.

### Crear e identificar una tarea

Los nombres de tareas son útiles en diagnósticos, mientras el objeto de tarea conserva el resultado:

```python
import asyncio

from orionis.aio import Loop


async def fetch_total() -> int:
    await asyncio.sleep(0)
    return 42


async def main() -> tuple[str, int]:
    task = await Loop.createTask(fetch_total(), name="fetch-total")
    return task.get_name(), await task


print(Loop.run(main()))  # ('fetch-total', 42)
```

`createTask` programa la ejecución inmediatamente; esperar la tarea devuelta es lo que recupera su resultado.

Validación: **Executed successfully** en CPython 3.14.6.

### Llevar una operación async a código síncrono

Este ejemplo recorre la ruta del hilo worker porque `runSync` se llama mientras el loop de `main` está activo:

```python
from orionis.aio import Loop


async def lookup(code: str) -> str:
    return code.upper()


async def main() -> str:
    return Loop.runSync(lookup("orionis"))


print(Loop.run(main()))  # ORIONIS
```

El resultado vuelve sincrónicamente a `main`. Durante esa llamada, el hilo que ejecuta `main` está bloqueado, por lo que es preferible usar directamente `await lookup(...)` cuando la API circundante pueda ser async.

Validación: **Executed successfully** en CPython 3.14.6.

### Manejar un uso inválido del punto de entrada

Pasa el objeto corrutina que devuelve la llamada a una función async, no la propia función:

```python
from orionis.aio import Loop


async def main() -> int:
    return 1


try:
    Loop.run(main)  # type: ignore[arg-type]
except TypeError as error:
    print(str(error))  # A coroutine object is required
```

La validación ocurre antes de crear un loop.

Validación: **Executed successfully** en CPython 3.14.6.

## Configuración

Este módulo no consume claves de configuración ni variables de entorno de Orionis. La selección de factoría depende de la plataforma actual y de si `uvloop` se puede importar; no existe una opción pública para reemplazar esa selección. La factoría resuelta se almacena durante toda la vida del proceso.

## Integración con Orionis

- `orionis.mail` usa `Loop.execute` para mantener fuera del hilo del event loop activo el renderizado síncrono, almacenamiento en archivos y trabajo SMTP.
- `orionis.schemas.rules.unique` usa `Loop.runSync` porque su hook público de validación es síncrono mientras su comprobación de existencia utiliza operaciones asíncronas de base de datos.
- El ejecutable `reactor` del repositorio inicia `app.handleCommand(sys.argv)` con `Loop.run`.
- `Loop` no tiene provider y no se resuelve mediante el contenedor de servicios; basta con importarlo.

Estos son consumidores directos, no efectos secundarios del bootstrap. Importar `orionis.aio` no crea un loop, ejecutor ni aplicación.

## Errores y casos límite

- `run` lanza `TypeError("A coroutine object is required")` para una función corrutina, valor simple u otro objeto que no sea un objeto corrutina nativo.
- `run` lanza `RuntimeError` cuando el hilo que llama ya tiene un loop en ejecución. La corrutina proporcionada queda sin consumir y sigue perteneciendo al llamador.
- `execute` lanza `TypeError("The provided object is not callable")` antes de programar un objeto que no sea callable. Sin un loop en ejecución, su llamada a `asyncio.get_running_loop()` lanza `RuntimeError`.
- Las excepciones de los callables y corrutinas invocados se propagan; el módulo no las envuelve.
- `run` convierte un `KeyboardInterrupt` lanzado durante la ejecución de la corrutina en el entero `0`.
- `eventLoopContext` puede cancelar cualquier tarea pendiente asociada a su loop inactivo, no solo las tareas creadas dentro del contexto. Intencionalmente, no cierra ese loop.
- Un loop cerrado en el almacenamiento local del hilo se descarta y reemplaza en la siguiente llamada a `getEventLoop`.

## Rendimiento y concurrencia

La resolución de la factoría de loops y la detección de `uvloop` se almacenan para todo el proceso y están protegidas por un `threading.Lock` durante el primer uso. Las resoluciones posteriores usan una ruta rápida sin adquirir el lock.

Los loops inactivos se almacenan en `threading.local`, por lo que cada hilo recibe el suyo y las llamadas repetidas en ese hilo lo reutilizan hasta que se cierre. Un loop actualmente en ejecución siempre tiene prioridad sobre el valor almacenado.

`execute` usa el ejecutor predeterminado del loop actual para el trabajo síncrono; su capacidad y ciclo de vida pertenecen por tanto a ese event loop. `runSync` usa un `ThreadPoolExecutor(max_workers=1)` separado para todo el proceso y creado de forma diferida bajo un lock. En consecuencia, las llamadas concurrentes a `runSync` que necesiten el worker se serializan. El ejecutor se conserva en vez de cerrarse después de cada llamada.

`runSync` evita errores por loops anidados ejecutando la corrutina en otro hilo, pero es una llamada bloqueante y puede pausar el hilo del event loop llamador. `createTask` solo programa trabajo; la concurrencia depende de que la corrutina ceda el control.

## Compatibilidad

El paquete declara Python 3.14+ y utiliza la sintaxis de funciones genéricas de Python 3.14. La validación de este documento usó CPython 3.14.6 en Windows.

En Windows, la resolución de factoría omite `uvloop` e intenta usar `asyncio.ProactorEventLoop`; si ese atributo no está disponible, recurre a `asyncio.new_event_loop` o `asyncio.run` según corresponda. Fuera de Windows se prefiere un `uvloop` importable; si falla el import, se usa el `asyncio` estándar. El código del módulo no impone requisitos de servicios externos.

## Notas de verificación

Se inspeccionaron la implementación en `orionis/aio/loop.py`, las exportaciones del paquete, los consumidores directos del framework, `pyproject.toml` y `tests/aio`. Las 48 pruebas del módulo pasaron mediante el ejecutor de pruebas de Orionis en CPython 3.14.6. Los cinco programas de Inicio rápido/Ejemplos se ejecutaron correctamente en el entorno virtual del proyecto. Los ejemplos no requieren servicios externos.
