# `orionis.aio`

> Gestor del bucle de eventos de `asyncio`, seguro entre hilos y consciente de la plataforma, expuesto en una única clase totalmente estática.

🇬🇧 English version: [README.md](README.md)

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja en el framework](#dónde-encaja-en-el-framework)
  - [Mapa del módulo](#mapa-del-módulo)
  - [Resolución de la factoría de loops](#resolución-de-la-factoría-de-loops)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [`Loop`](#loop)
  - [Estado de clase](#estado-de-clase)
  - [`Loop.getEventLoop()`](#loopgeteventloop)
  - [`Loop.run()`](#looprun)
  - [`Loop.runSync()`](#looprunsync)
  - [`Loop.execute()`](#loopexecute)
  - [`Loop.createTask()`](#loopcreatetask)
  - [`Loop.eventLoopContext()`](#loopeventloopcontext)
  - [`Loop.isLoopRunning()`](#loopislooprunning)
  - [Helpers internos](#helpers-internos)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [1. Punto de entrada de la aplicación](#1-punto-de-entrada-de-la-aplicación)
  - [2. Llamar a código async desde código síncrono](#2-llamar-a-código-async-desde-código-síncrono)
  - [3. Ejecutar una función bloqueante desde una corrutina](#3-ejecutar-una-función-bloqueante-desde-una-corrutina)
  - [4. Programar una tarea en segundo plano](#4-programar-una-tarea-en-segundo-plano)
  - [5. Gestionar el ciclo de vida de un loop con limpieza](#5-gestionar-el-ciclo-de-vida-de-un-loop-con-limpieza)
  - [6. Argumentos rechazados](#6-argumentos-rechazados)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

`orionis.aio` es el dueño del ciclo de vida del bucle de eventos dentro del
framework: elige la implementación más rápida disponible en la plataforma
actual, cachea un loop por hilo, hace de puente entre código síncrono y
asíncrono en ambos sentidos y cancela las tareas pendientes cuando se sale de
un contexto gestionado. Todo se expone en una sola clase, `Loop`, cuyos
miembros son siempre `@staticmethod` o `@classmethod`.

### Dónde encaja en el framework

`orionis/aio/loop.py` importa únicamente la biblioteca estándar (`asyncio`,
`concurrent.futures`, `functools`, `inspect`, `sys`, `threading`, `types`,
`contextlib`, `typing`); **no depende de ningún otro módulo de Orionis**, lo
que permite importarlo desde cualquier punto sin riesgo de import circular.

Consumidores directos dentro del framework:

| Consumidor | Miembro usado | Propósito |
| --- | --- | --- |
| `reactor` (punto de entrada de la CLI, en la raíz del repositorio) | `Loop.run(...)` | Ejecuta `app.handleCommand(sys.argv)` y entrega el resultado a `sys.exit`. |
| `orionis/schemas/rules/unique.py` | `Loop.runSync(...)` | Puentea el pipeline síncrono de reglas de validación hacia el ORM asíncrono. |

El módulo **no** se registra en el contenedor y **no tiene facade ni service
provider**: se importa y se usa directamente.

### Mapa del módulo

| Archivo | Contenido |
| --- | --- |
| `orionis/aio/__init__.py` | Reexporta `Loop`; `__all__ == ["Loop"]`. |
| `orionis/aio/loop.py` | La clase `Loop`: estado de clase, cuatro helpers internos y siete miembros públicos. |

### Resolución de la factoría de loops

`_getLoopFactory()` resuelve la factoría **una sola vez por proceso** y cachea
el resultado:

1. `uvloop.new_event_loop` — solo cuando `_IS_WIN32` es `False` y el `import
   uvloop` tiene éxito.
2. `asyncio.ProactorEventLoop` — solo cuando `_IS_WIN32` es `True`; protegido
   con `contextlib.suppress(AttributeError)` para que un runtime que no lo
   exponga siga adelante.
3. `None` — significa «que decida asyncio»; quien llama usa entonces
   `asyncio.new_event_loop()`.

Comportamiento observado en la plataforma de este repositorio
(`sys.platform == "win32"`, CPython 3.14):

```text
Loop._IS_WIN32:      True
Loop._detectUvloop(): None
Loop._getLoopFactory(): <class 'asyncio.windows_events.ProactorEventLoop'>
Loop.getEventLoop():  ProactorEventLoop instance
```

### Decisiones de diseño

Estas notas describen decisiones que ya están en el código; son informativas,
no recomendaciones.

- **La clase como espacio de nombres, sin instancias.** Todos los atributos son
  `ClassVar` y todos los miembros son `@staticmethod`/`@classmethod`, así que
  la propia clase es el gestor compartido. `Loop` no declara `__init__` ni
  `__slots__`, de modo que `Loop()` sí funciona y produce un objeto con
  `__dict__` — esa instancia simplemente no aporta nada frente a la clase.
- **Un loop por hilo.** `_loop_local` es un `threading.local()`, así que un
  loop creado en un hilo nunca se entrega a otro.
- **Doble comprobación con lock, dos veces.** `_detectUvloop()` (import del
  módulo) y `_getSyncExecutor()` (creación del pool) leen el guard fuera del
  lock y lo releen dentro, de forma que la operación cara ocurre como máximo
  una vez aunque varios hilos compitan en la primera llamada.
- **Pool puente de un solo worker.** `runSync()` usa un
  `ThreadPoolExecutor(max_workers=1, thread_name_prefix="orionis-sync")` para
  ejecutar la corrutina en su propio loop cuando quien llama ya está dentro de
  uno.
- **API pública en lugar de internos.** `_getRunningLoop()` envuelve
  `asyncio.get_running_loop()` en un `try/except RuntimeError` en vez de leer
  detalles internos de CPython.
- **La limpieza nunca lanza.** `eventLoopContext()` agrupa las tareas
  canceladas con `return_exceptions=True` dentro de
  `contextlib.suppress(RuntimeError, asyncio.CancelledError)`, así el bloque
  `finally` no puede enmascarar la excepción que salió del `with`.

## Referencia de API

### `Loop`

```python
class Loop:
    ...
```

Se importa desde el paquete o desde el módulo de implementación:

```python
from orionis.aio import Loop
from orionis.aio.loop import Loop
```

Todos los miembros se invocan sobre la clase (`Loop.run(...)`). La clase guarda
todo su estado a nivel de clase, por lo que ese estado lo comparte el proceso
entero.

### Estado de clase

Declarado literalmente así:

```python
_IS_WIN32: ClassVar[bool] = sys.platform == "win32"
_loop_local: ClassVar[threading.local] = threading.local()
_uvloop_factory: ClassVar[Callable[[], asyncio.AbstractEventLoop] | None] = None
_uvloop_checked: ClassVar[bool] = False
_loop_lock: ClassVar[threading.Lock] = threading.Lock()
_loop_factory_resolved: ClassVar[bool] = False
_loop_factory_cached: ClassVar[
    Callable[[], asyncio.AbstractEventLoop] | None
] = None
_sync_executor: ClassVar[concurrent.futures.ThreadPoolExecutor | None] = None
_sync_executor_lock: ClassVar[threading.Lock] = threading.Lock()
```

| Atributo | Alcance | Lo escribe |
| --- | --- | --- |
| `_IS_WIN32` | Proceso | Se evalúa una vez al definir la clase. |
| `_loop_local` | Hilo | `getEventLoop()` guarda el loop creado como `_loop_local.loop`. |
| `_uvloop_factory`, `_uvloop_checked` | Proceso | `_detectUvloop()`. |
| `_loop_factory_cached`, `_loop_factory_resolved` | Proceso | `_getLoopFactory()`. |
| `_sync_executor` | Proceso | `_getSyncExecutor()`. |
| `_loop_lock`, `_sync_executor_lock` | Proceso | Nunca se reasignan; protegen las dos detecciones. |

Ni los loops cacheados por hilo ni `_sync_executor` los cierra o apaga nunca
este módulo.

### `Loop.getEventLoop()`

```python
@classmethod
def getEventLoop(cls) -> asyncio.AbstractEventLoop
```

Devuelve el bucle de eventos del hilo que llama, creándolo si hace falta.

Orden de resolución:

1. El loop que ya está corriendo en este hilo, si lo hay.
2. `_loop_local.loop`, si existe y su `is_closed()` es `False`.
3. Un loop nuevo construido con la factoría resuelta, o con
   `asyncio.new_event_loop()` cuando la factoría es `None`.

**Parámetros:** ninguno.

**Devuelve:** `asyncio.AbstractEventLoop`.

**Lanza:** nada propio.

**Efectos secundarios:** en la rama 3 llama a `asyncio.set_event_loop(loop)` y
guarda el loop en `_loop_local`. El módulo nunca cierra ese loop.

### `Loop.run()`

```python
@staticmethod
def run[T](coro: Coroutine[Any, Any, T]) -> T
```

Ejecuta una corrutina como punto de entrada de la aplicación, desde un hilo
**sin** loop en marcha. Usa `asyncio.Runner(loop_factory=...)` cuando hay una
factoría resuelta y, si no, `asyncio.run(coro)`.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Objeto corrutina a ejecutar. |

**Devuelve:** el valor producido por `coro`. Si la corrutina lanza
`KeyboardInterrupt`, la excepción se absorbe y se devuelve el literal `0` (un
`int`) en su lugar, sea cual sea `T`.

**Lanza:**

- `TypeError("A coroutine object is required")` cuando
  `isinstance(coro, types.CoroutineType)` es `False` — una *función* corrutina
  también se rechaza.
- `RuntimeError` propagado desde asyncio cuando ya hay un loop corriendo en el
  hilo que llama; en ese caso `coro` queda sin consumir. Usa `Loop.runSync()`
  para puentear hacia un loop en marcha. El mensaje pertenece a la biblioteca
  estándar y difiere entre las ramas `asyncio.Runner` y `asyncio.run` —
  observado en CPython 3.14 / Windows: `Cannot run the event loop while another
  loop is running`.
- Cualquier otra excepción lanzada dentro de la corrutina se propaga sin
  cambios.

**Efectos secundarios:** crea y cierra un loop dedicado a esa llamada; no usa
ni rellena la caché por hilo.

### `Loop.runSync()`

```python
@classmethod
def runSync[T](cls, coro: Coroutine[Any, Any, T]) -> T
```

Ejecuta una corrutina hasta el final de forma síncrona desde cualquier
contexto.

- Sin loop corriendo en el hilo que llama → delega en `Loop.run(coro)`.
- Con un loop corriendo → envía `Loop.run` al ejecutor compartido de un solo
  worker y bloquea en `.result()`, de modo que la corrutina obtiene su propio
  loop en otro hilo en lugar de bloquear al llamante.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Objeto corrutina a ejecutar. |

**Devuelve:** el valor producido por `coro` (o `0` cuando la corrutina lanza
`KeyboardInterrupt`, heredado de `Loop.run`).

**Lanza:** lo que lance `coro`, relanzado en el hilo llamante por
`concurrent.futures.Future.result()`; además del mismo `TypeError` que
`Loop.run()` ante un argumento inválido.

**Efectos secundarios:** bloquea el hilo llamante hasta que la corrutina
termina y puede crear el ejecutor puente del proceso en el primer uso.

### `Loop.execute()`

```python
@staticmethod
async def execute(
    func: Callable[..., Any],
    /,
    *args: Any,
    **kwargs: Any,
) -> Any
```

Invoca un callable que puede ser síncrono o asíncrono desde dentro de una
corrutina, sin que quien llama tenga que ramificar según su naturaleza.

- `inspect.iscoroutinefunction(func)` → se hace `await` directamente sobre el
  loop en marcha.
- En caso contrario → se envuelve en `functools.partial(func, *args, **kwargs)`
  y se envía al ejecutor **por defecto** del loop mediante
  `loop.run_in_executor(None, ...)`.
- Si la llamada síncrona devuelve un objeto con `__await__`, ese objeto se
  awaitea antes de retornar.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `func` | `Callable[..., Any]` | Callable a invocar; solo posicional. |
| `*args` | `Any` | Argumentos posicionales reenviados a `func`. |
| `**kwargs` | `Any` | Argumentos nombrados reenviados a `func`. |

**Devuelve:** el resultado de `func`, o el resultado de awaitarlo cuando es
awaitable.

**Lanza:** `TypeError("The provided object is not callable")` cuando `func` no
es invocable; los errores de `func` se propagan sin cambios. Llama a
`asyncio.get_running_loop()` en la rama síncrona, así que debe awaitarse desde
un loop en marcha.

### `Loop.createTask()`

```python
@staticmethod
async def createTask[T](
    coro: Coroutine[Any, Any, T],
    *,
    name: str | None = None,
) -> asyncio.Task[T]
```

Programa `coro` en el loop en marcha mediante
`asyncio.get_running_loop().create_task(coro, name=name)`.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Corrutina a programar. |
| `name` | `str \| None` | Nombre opcional de la tarea; solo por nombre, por defecto `None`. |

**Devuelve:** `asyncio.Task[T]`.

**Lanza:** el `RuntimeError` que emite `asyncio.get_running_loop()` cuando no
hay ningún loop corriendo.

Ten en cuenta que el propio miembro es una función corrutina: la tarea se
obtiene con `task = await Loop.createTask(...)` y se awaitea una segunda vez
para recoger su resultado.

### `Loop.eventLoopContext()`

```python
@staticmethod
@contextmanager
def eventLoopContext() -> Generator[asyncio.AbstractEventLoop]
```

Gestor de contexto que cede `Loop.getEventLoop()` y realiza una limpieza
cooperativa al salir.

La limpieza solo se ejecuta si, al salir, el loop **no** está corriendo *y*
`asyncio.all_tasks(loop)` no está vacío. En ese caso se cancela cada tarea
pendiente y después se esperan todas con `asyncio.gather(*pending,
return_exceptions=True)` a través de `loop.run_until_complete(...)`.

**Parámetros:** ninguno.

**Cede:** `asyncio.AbstractEventLoop`.

**Lanza:** nada — los `RuntimeError` y `asyncio.CancelledError` que surjan
durante la limpieza se suprimen por diseño.

**Efectos secundarios:** cancela las tareas pendientes del loop cedido. El loop
**no** se cierra, así que sigue cacheado para el hilo.

### `Loop.isLoopRunning()`

```python
@staticmethod
def isLoopRunning() -> bool
```

Informa de si hay un bucle de eventos corriendo en el hilo que llama.

**Parámetros:** ninguno.

**Devuelve:** `bool` — `True` cuando `_getRunningLoop()` no es `None`.

**Lanza:** nada.

### Helpers internos

Se documentan porque definen las garantías de caché de los miembros públicos;
no forman parte de la superficie soportada.

```python
@staticmethod
def _getRunningLoop() -> asyncio.AbstractEventLoop | None

@classmethod
def _detectUvloop(cls) -> Callable[[], asyncio.AbstractEventLoop] | None

@classmethod
def _getLoopFactory(cls) -> Callable[[], asyncio.AbstractEventLoop] | None

@classmethod
def _getSyncExecutor(cls) -> concurrent.futures.ThreadPoolExecutor
```

- `_getRunningLoop()` — `asyncio.get_running_loop()` envuelto en
  `try/except RuntimeError`, devolviendo `None` en lugar de lanzar.
- `_detectUvloop()` — importa `uvloop` como máximo una vez por proceso y solo
  fuera de Windows; el `ImportError` se absorbe y el resultado se cachea en
  `_uvloop_factory`.
- `_getLoopFactory()` — aplica el orden de resolución descrito arriba y cachea
  la respuesta en `_loop_factory_cached`.
- `_getSyncExecutor()` — crea el pool puente de un solo worker en el primer uso
  y devuelve siempre la misma instancia después.

## Ejemplos de uso

Cada fragmento siguiente es un script completo que se puede ejecutar tal cual
con `python <archivo>.py`.

### 1. Punto de entrada de la aplicación

```python
import asyncio
from orionis.aio import Loop


async def main() -> int:
    print("Application started")
    await asyncio.sleep(0.1)
    return 0


exit_code = Loop.run(main())
print("exit code:", exit_code)
```

Salida:

```text
Application started
exit code: 0
```

Este es el patrón que usa la CLI `reactor`, que pasa el valor devuelto
directamente a `sys.exit(...)`.

### 2. Llamar a código async desde código síncrono

```python
from orionis.aio import Loop


async def fetch_greeting() -> str:
    return "Hello from an async task"


def sync_entrypoint() -> str:
    # Same call works with or without a loop already running in this thread.
    return Loop.runSync(fetch_greeting())


async def async_entrypoint() -> str:
    return Loop.runSync(fetch_greeting())


print("no loop running:", sync_entrypoint())
print("loop running:", Loop.run(async_entrypoint()))
```

Salida:

```text
no loop running: Hello from an async task
loop running: Hello from an async task
```

### 3. Ejecutar una función bloqueante desde una corrutina

```python
import time
from orionis.aio import Loop


def slow_blocking_call(seconds: float) -> str:
    time.sleep(seconds)
    return "blocking call finished"


async def handler() -> None:
    print(await Loop.execute(slow_blocking_call, 0.2))
    print(await Loop.execute(slow_blocking_call, seconds=0.1))


Loop.run(handler())
```

Salida:

```text
blocking call finished
blocking call finished
```

### 4. Programar una tarea en segundo plano

```python
import asyncio
from orionis.aio import Loop


async def background_job() -> str:
    await asyncio.sleep(0.05)
    return "background job finished"


async def controller() -> None:
    print("loop running:", Loop.isLoopRunning())
    task = await Loop.createTask(background_job(), name="warmup")
    print("task name:", task.get_name())
    print("task result:", await task)


Loop.run(controller())
```

Salida:

```text
loop running: True
task name: warmup
task result: background job finished
```

### 5. Gestionar el ciclo de vida de un loop con limpieza

```python
import asyncio
from orionis.aio import Loop


async def pending_forever() -> None:
    await asyncio.sleep(3600)


def run_batch() -> None:
    with Loop.eventLoopContext() as loop:
        leftover = loop.create_task(pending_forever())
        loop.run_until_complete(asyncio.sleep(0))
    print("leftover cancelled:", leftover.cancelled())
    print("loop closed:", loop.is_closed())


run_batch()
```

Salida:

```text
leftover cancelled: True
loop closed: False
```

### 6. Argumentos rechazados

```python
from orionis.aio import Loop


async def noop() -> None:
    return None


try:
    Loop.run(noop)
except TypeError as error:
    print("run:", error)


async def guard() -> None:
    try:
        await Loop.execute(42)
    except TypeError as error:
        print("execute:", error)


Loop.run(guard())
```

Salida:

```text
run: A coroutine object is required
execute: The provided object is not callable
```

## Consideraciones de rendimiento y concurrencia

- **La detección de plataforma ocurre una sola vez.** `_detectUvloop()` y
  `_getLoopFactory()` cachean su resultado en atributos de clase, así que las
  llamadas repetidas a `getEventLoop()`, `run()` o `runSync()` nunca repiten el
  import ni la comprobación de plataforma.
- **Camino rápido cuando ya hay un loop.** `getEventLoop()` e
  `isLoopRunning()` resuelven con una única llamada a
  `asyncio.get_running_loop()` dentro de un `try/except`, que es el caso normal
  dentro de un manejador de peticiones.
- **Aislamiento por hilo.** La caché de loops vive en un `threading.local()`,
  así que dos hilos que llamen a `getEventLoop()` reciben dos loops distintos;
  en ese camino no se toma ningún lock.
- **`runSync()` bloquea y serializa.** Bloquea el hilo llamante hasta que la
  corrutina termina, y el pool puente tiene exactamente **un** worker, así que
  varias llamadas concurrentes a `runSync()` hechas desde dentro de un loop en
  marcha se encolan una detrás de otra en vez de ejecutarse en paralelo.
- **`execute()` usa el ejecutor por defecto de asyncio**, no el pool puente de
  un worker, de modo que su paralelismo es el que provea el ejecutor por
  defecto del loop en marcha.
- **La limpieza es condicional.** `eventLoopContext()` cancela tareas solo si
  el loop está inactivo al salir; si el loop sigue corriendo, el bloque termina
  sin tocar ninguna tarea.
- **`run()` construye un loop nuevo por llamada.** Nunca reutiliza el loop del
  hilo, así que está pensado para puntos de entrada y no para caminos
  calientes.
- **Nada se desmonta.** Ni los loops por hilo ni el ejecutor puente los cierra
  este módulo; viven hasta que el proceso termina.

## Notas de compatibilidad

- **Python:** `>= 3.14`, tal como declara `pyproject.toml`. El módulo usa la
  sintaxis genérica del PEP 695 (`def run[T](...)`, `def createTask[T](...)`,
  `def runSync[T](...)`), que es un error de sintaxis en intérpretes
  anteriores.
- **Dependencias:** solo biblioteca estándar. `uvloop>=0.22.1` es una
  dependencia base del framework restringida a `sys_platform != 'win32'`, así
  que no hay que instalar nada extra; cuando es importable se usa
  automáticamente y, cuando no lo es, el `ImportError` se absorbe.
- **El comportamiento por plataforma difiere a propósito:** Windows resuelve a
  `asyncio.ProactorEventLoop`, el resto de plataformas a `uvloop` cuando está
  disponible y al valor por defecto de asyncio en caso contrario.
- **Anotaciones de tipo:** el módulo usa `from __future__ import annotations`,
  así que sus anotaciones son cadenas en tiempo de ejecución; la clase nunca la
  construye el contenedor de inyección de dependencias, que resuelve de forma
  ansiosa las anotaciones de los constructores.
- **Superficie pública:** `orionis/aio/__init__.py` exporta exactamente `Loop`
  (`__all__ == ["Loop"]`).
