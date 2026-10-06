# orionis.aio

> Selecciona bucles, ejecuta corrutinas nativas, deriva callables y programa tareas.

Versión en inglés: [README.md](README.md). Entrada para agentes:
[SKILL.md](SKILL.md).

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Loop](#loop)
- [Loop.getEventLoop()](#loopgeteventloop)
- [Loop.run()](#looprun)
- [Loop.runSync()](#looprunsync)
- [Loop.execute()](#loopexecute)
- [Loop.createTask()](#loopcreatetask)
- [Loop.eventLoopContext()](#loopeventloopcontext)
- [Loop.isLoopRunning()](#loopislooprunning)
- [Ejemplos de uso](#ejemplos-de-uso)
- [1. Ejecutar una corrutina de entrada](#1-ejecutar-una-corrutina-de-entrada)
- [2. Hacer de puente desde código síncrono](#2-hacer-de-puente-desde-código-síncrono)
- [3. Ejecutar ambos tipos de callable](#3-ejecutar-ambos-tipos-de-callable)
- [4. Programar y esperar tareas con nombre](#4-programar-y-esperar-tareas-con-nombre)
- [5. Limpiar un bucle detenido](#5-limpiar-un-bucle-detenido)
- [6. Manejar entradas rechazadas y ejecución anidada](#6-manejar-entradas-rechazadas-y-ejecución-anidada)
- [7. Integrar FreezeThaw](#7-integrar-freezethaw)
- [8. Procesar archivos JSON temporales concurrentemente](#8-procesar-archivos-json-temporales-concurrentemente)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Descripción funcional

`orionis.aio` expone `Loop` para seleccionar u obtener un bucle de eventos,
ejecutar una corrutina nativa síncronamente, despachar callables de forma
asíncrona y crear tareas. Su gestor de contexto cancela condicionalmente las
tareas pendientes de un bucle detenido. La implementación usa la biblioteca
estándar y detecta `uvloop` de forma diferida; no requiere preparación adicional
a la instalación del framework.

Consumidores directos verificados, sin pretender un catálogo exhaustivo:

| Fuente y símbolo | Relación |
| --- | --- |
| [reactor](../../../reactor), `__main__` | Entrega `app.handleCommand(sys.argv)` a `Loop.run()` y su resultado a `sys.exit()`. |
| [orionis/schemas/rules/unique.py](../../schemas/rules/unique.py), `Unique.enforce()` | Usa `Loop.runSync()` para la validación síncrona de unicidad; la ruta asíncrona espera directamente la conexión actual. |
| [orionis/mail/composer.py](../../mail/composer.py), `MailComposer.prepare()` | Espera `Loop.execute()` para componer datos MIME con su auxiliar síncrono `_compose()`. |

Estos consumidores importan `Loop` directamente. El módulo asignado no contiene
proveedor, facade, clase de contrato ni archivo de configuración. El ejemplo de
integración utiliza [orionis/support/structures/freezer.py](../../support/structures/freezer.py),
`FreezeThaw.freeze()` y `FreezeThaw.thaw()`, sin arrancar una aplicación.

## Estructura del módulo

Las rutas de las etiquetas de los enlaces son relativas a la raíz del
repositorio; sus destinos son relativos a este documento.

| Archivo inspeccionado | Responsabilidad y símbolos públicos |
| --- | --- |
| [orionis/aio/__init__.py](../__init__.py) | Reexporta por identidad el `Loop` de la implementación; `__all__ = ["Loop"]`. |
| [orionis/aio/loop.py](../loop.py) | Define `Loop`, sus siete métodos públicos, cuatro auxiliares privados, y cachés y bloqueos de clase. |

Ambos archivos Python se inspeccionaron completos. Este módulo no tiene
subpaquetes Python ni recursos utilizados durante la ejecución. Sus tres
documentos son material de referencia, no entradas de ejecución.

## Referencia de API

Los siguientes bloques son **fragmentos literales de referencia**, incluidos
decoradores y comentarios fuente. Omiten los cuerpos y no son scripts
ejecutables. El descriptor `@classmethod` proporciona `cls`, no quien llama.
Las listas de excepciones distinguen comprobaciones explícitas y errores
propagados; no son exhaustivas cuando intervienen un callable, una factoría de
tareas o de bucles, o un ejecutor.

### Loop

Fuente: [orionis/aio/loop.py](../loop.py#L15), `Loop`. Exportación del paquete:
[orionis/aio/__init__.py](../__init__.py).

```python
class Loop:
```

Usa `from orionis.aio import Loop` o `from orionis.aio.loop import Loop`.
La clase no tiene clase base, constructor explícito, propiedades, sobrecargas
ni métodos especiales propios. Sus once métodos declarados son métodos de
clase o estáticos; solo los siete sin guion bajo son API de consumo.

`Loop()` utiliza el constructor heredado de `object` y está permitido. La
instancia tiene `__dict__` porque no se declara `__slots__`, pero su construcción
no crea un bucle ni un pool, y los métodos siguen usando estado de clase.
Invoca los métodos sobre `Loop`; no hay métodos públicos para reiniciar la
caché, cerrar bucles o apagar el pool. Los auxiliares privados y los nombres
importados de la biblioteca estándar no son API públicas adicionales; sus
mecanismos relevantes se explican en diseño y concurrencia.

### Loop.getEventLoop()

Fuente: [orionis/aio/loop.py](../loop.py#L186), `Loop.getEventLoop`.

```python
@classmethod
def getEventLoop(cls) -> asyncio.AbstractEventLoop:
```

**Parámetros:** ninguno proporcionado por quien llama. **Resultado:** el bucle
en marcha en el hilo llamante; si no existe, un bucle abierto retenido en la
caché de ese hilo; si tampoco existe, un nuevo `asyncio.AbstractEventLoop`.

La rama de creación selecciona la factoría cacheada, con
`asyncio.new_event_loop()` como alternativa, llama a
`asyncio.set_event_loop(loop)` y guarda `_loop_local.loop`. Un bucle cacheado
cerrado se reemplaza. Un bucle en marcha se devuelve sin escribirlo en esta
caché. La rama de caché no consulta un bucle ajeno registrado externamente con
`asyncio.set_event_loop()`.

No hay un `raise` explícito ni traducción general de excepciones: los errores
de factorías, imports o registro de asyncio pueden propagarse. Obtener el bucle
no lo inicia ni lo cierra. Su propietario debe organizar el cierre necesario;
el ejemplo 5 cierra explícitamente el bucle detenido que toma prestado.

### Loop.run()

Fuente: [orionis/aio/loop.py](../loop.py#L213), `Loop.run`.

```python
@staticmethod
def run[T](coro: Coroutine[Any, Any, T]) -> T:
```

| Parámetro | Anotación declarada | Valor admitido |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Objeto corrutina nativo, como el resultado de llamar a un `async def`; sin valor predeterminado. |

**Resultado:** el resultado de la corrutina. Un `KeyboardInterrupt` capturado
durante la ejecución o el cierre del runner devuelve el entero literal `0`,
aunque `T` no sea `int`. Por tanto, la anotación de retorno no describe ese
resultado excepcional.

**Errores explícitos:** `TypeError("A coroutine object is required")` salvo que
`isinstance(coro, types.CoroutineType)` sea verdadero. Una función, `None`, una
tarea, un future o un awaitable no nativo falla esa comprobación. Si ya hay un
bucle en marcha en el hilo llamante, el propio método lanza `RuntimeError` antes
de abrir un runner: `"Runner.run() cannot be called from a running event loop"`
cuando hay factoría seleccionada; en caso contrario,
`"asyncio.run() cannot be called from a running event loop"`. La corrutina nativa
queda sin consumir; ciérrala o espérala de forma apropiada.

**Errores propagados:** los errores de la corrutina distintos del
`KeyboardInterrupt` capturado, los errores de factoría y los del runner no se
traducen en general. Reutilizar una corrutina consumida pasó la comprobación de
tipo nativo, pero lanzó `RuntimeError("cannot reuse already awaited coroutine")`
en el entorno validado.

Con factoría, el método usa `with asyncio.Runner(loop_factory=factory)`;
sin ella, usa `asyncio.run(coro)`. El runner posee un bucle nuevo y se encarga de
su cierre. Esto no consume ni rellena la caché de bucles por hilo de `Loop`.
La resolución de factoría y la comprobación del bucle activo preceden al
manejador de `KeyboardInterrupt`. Usa `run()` en un punto de entrada sin bucle
activo en ese hilo.

### Loop.runSync()

Fuente: [orionis/aio/loop.py](../loop.py#L372), `Loop.runSync`;
el pool se inicializa en `Loop._getSyncExecutor` en el mismo archivo.

```python
@classmethod
def runSync[T](cls, coro: Coroutine[Any, Any, T]) -> T:
```

| Parámetro | Anotación declarada | Valor admitido |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Objeto corrutina nativo admitido por `run()`; sin valor predeterminado. |

Sin bucle activo en el hilo llamante, delega en `cls.run(coro)`. En caso
contrario, envía `cls.run` al
`ThreadPoolExecutor(max_workers=1, thread_name_prefix="orionis-sync")` cacheado
y espera en `.result()` **sin timeout**. La corrutina se ejecuta entonces en
un bucle separado del worker, mientras el hilo llamante, incluido su bucle de
eventos, permanece bloqueado.

**Resultado:** el de `run()`, incluido el entero `0` ante un
`KeyboardInterrupt` manejado. **Errores:** los errores de validación y ejecución
de `run()` llegan directamente al llamante o mediante el future del ejecutor;
también pueden propagarse errores del ejecutor. La rama con bucle activo puede
crear el pool incluso para una entrada inválida, porque la validación de la
corrutina nativa ocurre dentro del `run()` enviado.

El worker y el pool se comparten en la clase; los argumentos no se clonan.
No envíes trabajo que dependa del progreso del llamante bloqueado o que requiera
recursivamente el mismo único worker. Este puente no vuelve portables los
clientes ligados a un bucle. Consulta arriba `Unique.enforce()` como consumidor
real que crea una conexión aislada para la rama que cruza bucles.

### Loop.execute()

Fuente: [orionis/aio/loop.py](../loop.py#L266), `Loop.execute`.

```python
@staticmethod
async def execute(
        func: Callable[..., Any],
        /,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
```

| Parámetro | Anotación declarada | Significado |
| --- | --- | --- |
| `func` | `Callable[..., Any]` | Callable a invocar; obligatorio y solo posicional. |
| `*args` | `Any` | Argumentos posicionales reenviados sin cambios; pueden estar vacíos. |
| `**kwargs` | `Any` | Argumentos nombrados reenviados sin cambios; pueden estar vacíos. |

**Resultado al esperar:** si `inspect.iscoroutinefunction(func)` es verdadero,
devuelve directamente `await func(*args, **kwargs)`. En caso contrario, envía un
`functools.partial` al **ejecutor por defecto** del bucle actual, espera el
resultado y solo lo espera de nuevo si `hasattr(result, "__await__")` es verdadero.
Un resultado ordinario, incluido `None`, se devuelve sin cambios.

Esta última comprobación usa un atributo, no `inspect.isawaitable()`. Un
awaitable basado en generador sin `__await__` se devolvió sin cambios en la
comprobación de ejecución. En cambio, un objeto con `__await__` inválido puede
fallar al esperarlo. Las instancias callable no detectadas como funciones
corrutina toman la ruta del ejecutor; una corrutina nativa que devuelvan se
espera después en el bucle llamante.

**Error explícito:** `TypeError("The provided object is not callable")` cuando
`callable(func)` es falso. **Errores propagados:** errores al enlazar argumentos,
errores del callable, de espera, cancelación y errores del ejecutor. En la rama
síncrona, `asyncio.get_running_loop()` también lanza `RuntimeError` si la
corrutina se impulsa sin un bucle en marcha.

Llamar a `execute()` solo construye su corrutina; la invocación sucede al
esperarla. No copia argumentos, cierra recursos devueltos, protege trabajo con
shield ni espera el worker después de una cancelación. Un worker ya iniciado
continuó ejecutándose tras cancelar la tarea que lo esperaba en la comprobación
aislada. Consulta el ejemplo 3 y la sección de concurrencia.

### Loop.createTask()

Fuente: [orionis/aio/loop.py](../loop.py#L350), `Loop.createTask`.

```python
@staticmethod
async def createTask[T](
        coro: Coroutine[Any, Any, T],
        *,
        name: str | None = None,
) -> asyncio.Task[T]:
```

| Parámetro | Anotación declarada | Significado |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Corrutina enviada directamente al `create_task()` del bucle en marcha; obligatoria. |
| `name` | `str \| None` | Nombre opcional de la tarea; solo por nombre, con `None` por defecto. |

**Resultado al esperar:** una `asyncio.Task[T]` programada, no el valor de la
tarea terminada. Usa `task = await Loop.createTask(coro)` y después
`result = await task`. El propio método no suspende después de llamar a
`create_task()`, pero invocarlo sin esperarlo no programa `coro`.

No hay validación del módulo: la validación de entradas y la programación
pertenecen a `asyncio.get_running_loop().create_task(coro, name=name)`, incluida
cualquier factoría de tareas personalizada. La ausencia de bucle activo propaga
`RuntimeError`; las corrutinas inválidas pueden propagar `TypeError`. Los
errores de la tarea aparecen al esperar la tarea devuelta, no como resultado
completado de este auxiliar. No se añaden registro de tareas, espera automática,
cancelación ni sustitución de la factoría de tareas.

### Loop.eventLoopContext()

Fuente: [orionis/aio/loop.py](../loop.py#L314), `Loop.eventLoopContext`.

```python
@staticmethod
@contextmanager
def eventLoopContext() -> Generator[asyncio.AbstractEventLoop]:
```

**Parámetros:** ninguno. `@contextmanager` proporciona un gestor de contexto
**síncrono**, usado con `with`, no con `async with`. Al entrar obtiene
`Loop.getEventLoop()`; el generador cede ese bucle una vez. La anotación de
generador de la declaración describe el generador subyacente de la función
decorada, no el tipo del objeto gestor de contexto devuelto externamente.

Al salir, si el bucle no está en marcha, el método toma una instantánea de
`asyncio.all_tasks(loop)`. Si el conjunto no está vacío, llama a `cancel()` en
cada tarea incluida y las espera con
`loop.run_until_complete(asyncio.gather(..., return_exceptions=True))`. Esto
incluye tareas pendientes ajenas del bucle prestado, no solo las creadas dentro
del bloque. Las tareas completadas no están en ese conjunto. No hay cierre del
bucle, cierre de generadores asíncronos, apagado del ejecutor ni timeout de
limpieza.

Si el bucle está en marcha al salir, **se omite toda la limpieza**. Sin tareas
pendientes no se ejecuta un gather. La región de limpieza solo suprime
`RuntimeError` y `asyncio.CancelledError`; los fallos de adquisición suceden
antes de ella. Las excepciones ordinarias de tareas devueltas por `gather` se
descartan. Una excepción del cuerpo se propaga cuando la limpieza termina;
no deduzcas supresión universal de excepciones a partir de la docstring. Es
posible volver a usar un bucle cacheado abierto, pero una instancia del gestor
de contexto decorado no es un objeto reutilizable de ciclo de vida.

### Loop.isLoopRunning()

Fuente: [orionis/aio/loop.py](../loop.py#L339), `Loop.isLoopRunning`;
el auxiliar de detección `Loop._getRunningLoop` comienza en el mismo archivo
en [la declaración del auxiliar](../loop.py#L70).

```python
@staticmethod
def isLoopRunning() -> bool:
```

**Parámetros:** ninguno. **Resultado:** si `asyncio.get_running_loop()` tiene
éxito en el hilo llamante. El auxiliar convierte su `RuntimeError` en `None`;
este método indica si el resultado no es `None`. No crea bucles ni modifica
cachés. Un bucle cacheado pero detenido, o uno en marcha en otro hilo, no vuelve
verdadero el resultado. El método no lanza errores explícitos; los errores
inesperados distintos del `RuntimeError` capturado por el auxiliar no se traducen.

## Ejemplos de uso

Cada bloque de esta sección es un script independiente para Python 3.14+ con el
framework instalado o la raíz del repositorio en `PYTHONPATH`. No se necesitan
arranque de aplicación, credenciales ni servicios externos. Las aserciones
definen el comportamiento esperado; cada script solo imprime `example-N: OK`
cuando pasan sus aserciones. No combines estos scripts en un proceso compartido
al verificar estado de clase.

### 1. Ejecutar una corrutina de entrada

La corrutina nativa termina su ejecución y expone su bucle solo mientras está
activa.

```python
import asyncio
from orionis.aio import Loop


async def main() -> int:
        assert Loop.isLoopRunning()
        assert Loop.getEventLoop() is asyncio.get_running_loop()
        await asyncio.sleep(0)
        return sum((10, 20, 30))


assert not Loop.isLoopRunning()
assert Loop.run(main()) == 60
assert not Loop.isLoopRunning()
print("example-1: OK")
```

### 2. Hacer de puente desde código síncrono

Sin bucle activo, la corrutina se ejecuta en el hilo llamante. Dentro de uno,
`runSync()` bloquea mientras la corrutina independiente se ejecuta en el worker
puente.

```python
import threading
from orionis.aio import Loop


async def identify_thread() -> int:
        return threading.get_ident()


async def inside_loop() -> int:
        assert Loop.isLoopRunning()
        return Loop.runSync(identify_thread())


caller_thread = threading.get_ident()
assert Loop.runSync(identify_thread()) == caller_thread
assert Loop.run(inside_loop()) != caller_thread
print("example-2: OK")
```

### 3. Ejecutar ambos tipos de callable

La invocación síncrona utiliza otro hilo; las funciones corrutina y las
corrutinas nativas devueltas por factorías síncronas se esperan en el bucle
llamante.

```python
import asyncio
import threading
from orionis.aio import Loop


async def append_suffix(value: str, *, suffix: str) -> str:
        await asyncio.sleep(0)
        return value + suffix


def coroutine_factory(value: str, *, suffix: str) -> object:
        return append_suffix(value, suffix=suffix)


async def main() -> None:
        caller_thread = threading.get_ident()
        assert await Loop.execute(threading.get_ident) != caller_thread
        assert await Loop.execute(append_suffix, "direct", suffix="!") == "direct!"
        factory_result = await Loop.execute(
                coroutine_factory, "factory", suffix="!",
        )
        assert factory_result == "factory!"


Loop.run(main())
print("example-3: OK")
```

### 4. Programar y esperar tareas con nombre

Crear una tarea y esperar su valor son operaciones separadas. La limpieza
espera todas las tareas retenidas por este ejemplo, incluso ante un fallo
intermedio.

```python
import asyncio
from orionis.aio import Loop


async def square(value: int) -> int:
        await asyncio.sleep(0)
        return value * value


async def main() -> None:
        tasks: list[asyncio.Task[int]] = []
        try:
                for value in range(4):
                        task = await Loop.createTask(
                                square(value), name=f"square-{value}",
                        )
                        tasks.append(task)
                assert [task.get_name() for task in tasks] == [
                        f"square-{value}" for value in range(4)
                ]
                assert await asyncio.gather(*tasks) == [0, 1, 4, 9]
        finally:
                for task in tasks:
                        if not task.done():
                                task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)


Loop.run(main())
print("example-4: OK")
```

### 5. Limpiar un bucle detenido

El contexto cancela una tarea pendiente, conserva abierto el bucle y permite
volver a usarlo. El script cierra ese bucle por su cuenta y comprueba la
sustitución de la entrada de caché cerrada.

```python
import asyncio
from orionis.aio import Loop


async def wait_forever() -> None:
        await asyncio.Event().wait()


loop = Loop.getEventLoop()
try:
    assert Loop.getEventLoop() is loop
    with Loop.eventLoopContext() as borrowed:
        assert borrowed is loop
        leftover = borrowed.create_task(wait_forever())
        borrowed.run_until_complete(asyncio.sleep(0))
    assert leftover.cancelled()
    assert not loop.is_closed()
    assert not Loop.isLoopRunning()
finally:
    loop.close()
    asyncio.set_event_loop(None)

replacement = Loop.getEventLoop()
try:
    assert replacement is not loop and not replacement.is_closed()
finally:
    replacement.close()
    asyncio.set_event_loop(None)
print("example-5: OK")
```

### 6. Manejar entradas rechazadas y ejecución anidada

Estos son errores reales de validación del módulo. La corrutina nativa
rechazada sigue sin iniciarse y su propietario la cierra explícitamente
después del intento de ejecución anidada.

```python
from orionis.aio import Loop


async def noop() -> None:
        return None


try:
    Loop.run(noop)
except TypeError as error:
    assert str(error) == "A coroutine object is required"
else:
    raise AssertionError("A coroutine function was accepted")


async def check_errors() -> None:
    try:
        await Loop.execute(42)
    except TypeError as error:
        assert str(error) == "The provided object is not callable"
    else:
        raise AssertionError("A non-callable value was accepted")

    coroutine = noop()
    try:
        try:
            Loop.run(coroutine)
        except RuntimeError:
            pass
        else:
            raise AssertionError("A nested runner was accepted")
    finally:
        coroutine.close()


Loop.run(check_errors())
print("example-6: OK")
```

### 7. Integrar FreezeThaw

`Loop.execute()` devuelve el resultado real del otro componente de Orionis.
Esta integración usa una estructura local acíclica; no atribuye a este módulo
la semántica de congelación ni la gestión de configuración de aplicaciones.

```python
from types import MappingProxyType
from orionis.aio import Loop
from orionis.support.structures.freezer import FreezeThaw


async def main() -> None:
        payload = {"names": ["Ada", "Linus"]}
        frozen = await Loop.execute(FreezeThaw.freeze, payload)
        assert isinstance(frozen, MappingProxyType)
        assert frozen["names"] == ("Ada", "Linus")
        editable = await Loop.execute(FreezeThaw.thaw, frozen)
        assert isinstance(editable, dict)
        editable["names"].append("Grace")
        assert editable["names"] == ["Ada", "Linus", "Grace"]
        assert payload["names"] == ["Ada", "Linus"]
        assert frozen["names"] == ("Ada", "Linus")


Loop.run(main())
print("example-7: OK")
```

### 8. Procesar archivos JSON temporales concurrentemente

Combina tareas con nombre, I/O de archivos síncrono despachado con `execute()`,
resultados ordenados, espera de tareas y limpieza del directorio temporal. No
es un benchmark ni una afirmación de que los hilos aceleren trabajo Python
limitado por CPU.

```python
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.aio import Loop


def read_scores(path: Path) -> list[int]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)["scores"]


async def summarize(path: Path) -> int:
        scores = await Loop.execute(read_scores, path)
        return sum(scores)


async def process(paths: tuple[Path, ...]) -> list[int]:
    tasks: list[asyncio.Task[int]] = []
    try:
        for path in paths:
            task = await Loop.createTask(summarize(path), name=path.stem)
            tasks.append(task)
        return list(await asyncio.gather(*tasks))
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


with TemporaryDirectory(prefix="orionis-aio-") as directory:
        paths: list[Path] = []
        for index, scores in enumerate(((1, 2), (3, 4), (5, 6))):
                path = Path(directory) / f"batch-{index}.json"
                path.write_text(json.dumps({"scores": scores}), encoding="utf-8")
                paths.append(path)
        assert Loop.run(process(tuple(paths))) == [3, 7, 11]
print("example-8: OK")
```

## Características de diseño

Todos los mecanismos siguientes están en
[orionis/aio/loop.py](../loop.py), `Loop`, salvo otro enlace explícito.

| Mecanismo observado | Consecuencia visible para el consumidor |
| --- | --- |
| `_getRunningLoop()` captura el `RuntimeError` de `asyncio.get_running_loop()`. | La detección es local al hilo llamante y no crea un bucle. |
| `_IS_WIN32` registra `sys.platform == "win32"` al definir la clase. | La selección de plataforma no se recalcula desde variables de entorno en cada llamada. |
| `_detectUvloop()` usa `_uvloop_checked`, `_uvloop_factory` y `_loop_lock`. | Fuera de Windows importa `uvloop` de forma diferida y cachea el éxito o `ImportError`; en Windows omite ese import. |
| `_getLoopFactory()` usa `_loop_factory_resolved` y `_loop_factory_cached`. | Selecciona el `uvloop.new_event_loop` detectado, después `asyncio.ProactorEventLoop` en Windows y, como alternativa final, `None`. Tolera la ausencia del atributo Proactor; `None` delega la creación en asyncio. |
| `_loop_local` es `threading.local()`. | Los bucles abiertos creados con `getEventLoop()` se retienen por hilo, sin cierre automático al terminar el hilo. |
| `_getSyncExecutor()` usa `_sync_executor` y `_sync_executor_lock`. | Inicializa un pool puente cacheado de un solo worker mediante doble comprobación con bloqueo. |
| `run()` y `eventLoopContext()` referencian `Loop` explícitamente; los métodos de clase usan `cls`. | Heredar no basta para personalizar la factoría o el estado de todas las operaciones. |
| `@contextmanager` envuelve un generador; `createTask()` es asíncrono. | Usa `with Loop.eventLoopContext()` y espera la creación de la tarea antes de esperar su resultado. |

Importar los dos archivos del módulo define la clase, crea su `threading.local`
y dos bloqueos, y reexporta `Loop`; no crea un bucle, un pool ni arranca una
aplicación. El resolvedor de exportaciones diferidas del paquete padre está en
[orionis/__init__.py](../../__init__.py) y
[orionis/_exports.py](../../_exports.py). Los imports verificados en procesos
aislados resolvieron a este repositorio, no a otra instalación del framework.

## Rendimiento y concurrencia

Evidencia: [orionis/aio/loop.py](../loop.py), especialmente
`Loop._detectUvloop`, `Loop._getLoopFactory`, `Loop._getSyncExecutor`,
`Loop.runSync`, `Loop.execute` y `Loop.eventLoopContext`.

- La detección y la creación del pool se difieren hasta que hacen falta. Las
  llamadas posteriores usan estado de clase cacheado, incluido un import
  fallido de `uvloop`; no hay invalidación pública ni control de capacidad
  para estas entradas fijas.
- La ruta con bucle activo de `getEventLoop()` evita la rama de creación por
  hilo. `run()` crea, en cambio, un bucle propiedad del runner por llamada válida.
- `_loop_lock` protege la detección de `uvloop` y `_sync_executor_lock` protege
  la creación del pool. Las escrituras finales de campos cacheados en
  `_getLoopFactory()` no tienen un bloqueo separado. Una caché por hilo no
  sincroniza tareas, callbacks ni recursos que los usuarios compartan
  explícitamente entre hilos.
- Los envíos concurrentes de `runSync()` desde bucles activos comparten un
  worker y se encolan; `.result()` bloquea sin timeout. La corrutina debe poder
  terminar independientemente del llamante bloqueado y de los envíos
  recursivos a ese worker. Las frases de docstrings sobre evitar interbloqueos
  no establecen un contrato universal libre de interbloqueos.
- `execute()` usa el ejecutor por defecto del bucle activo, no el pool puente.
  El paralelismo y la cola dependen de ese ejecutor. Las referencias capturadas
  por su `functools.partial` siguen vivas mientras el trabajo está encolado o
  ejecutándose; los argumentos mutables se comparten, no se copian. No hay una
  copia explícita de contexto por envío.
- Cancelar una espera de `execute()` no detiene un callable síncrono ya
  iniciado en un hilo. El módulo no añade shielding ni un protocolo de limpieza
  de recursos. La cancelación de la rama asíncrona sigue la del callback.
- `eventLoopContext()` materializa el conjunto de tareas pendientes y envía
  un gather. Solicita una cancelación por tarea incluida; estas deben cooperar.
  No hay timeout, y las tareas creadas después de la instantánea no se vuelven
  a buscar por separado.
- El módulo nunca apaga su pool puente cacheado ni cierra los bucles retenidos
  por `getEventLoop()`. Esto **no** se aplica al bucle dedicado que cada
  invocación de `run()` posee y cierra.

> ⚠️ No especificado en el código fuente: seguridad de todo el módulo ante
> acceso concurrente arbitrario desde varios hilos o bucles de eventos,
> equidad entre llamantes y propagación de variables de contexto por envío.

No se realizaron benchmarks ni se publicaron cifras de rendimiento, garantías
de tiempo constante o afirmaciones de aceleración del trabajo limitado por CPU
para esta tarea de documentación.

## Notas de compatibilidad

| Evidencia | Distinción verificada |
| --- | --- |
| [pyproject.toml](../../../pyproject.toml), `project.requires-python` | El mínimo declarado del framework es `>=3.14`; los ejemplos tienen como objetivo Python 3.14+. |
| [orionis/aio/loop.py](../loop.py), `run[T]`, `runSync[T]`, `createTask[T]` | La sintaxis de parámetros de tipo de funciones de PEP 695 requiere un parser que la admita, introducido en Python 3.12. Esto no declara soporte del framework para 3.12 ni 3.13. |
| [pyproject.toml](../../../pyproject.toml), `project.dependencies` | `uvloop>=0.22.1 ; sys_platform != 'win32'` es una dependencia **base** condicionada por plataforma, no un extra de Orionis. El código tolera su `ImportError` y usa asyncio como alternativa. |
| [uv.lock](../../../uv.lock), paquete `uvloop` | La versión resuelta es `0.23.0`; no es el mínimo soportado y no se instaló ni se ejecutó en Windows durante la validación. |
| Validación realizada | CPython `3.14.6`, `sys.platform == "win32"`; el bucle seleccionado fue `asyncio.windows_events.ProactorEventLoop`. |

Los demás imports de ejecución del módulo son de la biblioteca estándar.
`Callable`, `Coroutine` y `Generator` solo se importan bajo `TYPE_CHECKING`, y
`from __future__ import annotations` conserva anotaciones como cadenas. Por
ello, resolver tipos en ejecución no es automáticamente completo:
`typing.get_type_hints(Loop.run)` sin ayuda lanzó `NameError` para `Coroutine`
en la comprobación. Las declaraciones literales anteriores se copiaron del
código fuente, no de firmas evaluadas.

> ⚠️ No ejecutado en este entorno: un backend real de `uvloop`, ejecución fuera
> de Windows, otras versiones de Python y una compilación de Python sin GIL.

## Verificación y limitaciones

La cobertura del inventario público es completa: ambos archivos Python, la
clase `Loop` y su reexportación, y los siete métodos públicos. Los cuatro
auxiliares privados y nueve campos privados de estado de clase se explican
solo donde determinan el comportamiento público. Los imports de biblioteca
estándar, los nombres importados bajo `TYPE_CHECKING` y el atributo del submódulo
`loop` se excluyen como símbolos de consumo adicionales; no son API exportadas
por separado. No se encontraron excepciones públicas, constantes, propiedades,
protocolos, enumeraciones ni sobrecargas en el módulo asignado.

| Script | Sintaxis | Imports | Estado de ejecución |
| --- | --- | --- | --- |
| 1. Punto de entrada | Correcta | Repositorio local verificado | Ejecutado correctamente |
| 2. Puente síncrono | Correcta | Repositorio local verificado | Ejecutado correctamente |
| 3. Despacho de callables | Correcta | Repositorio local verificado | Ejecutado correctamente |
| 4. Tareas con nombre | Correcta | Repositorio local verificado | Ejecutado correctamente |
| 5. Contexto de bucle detenido | Correcta | Repositorio local verificado | Ejecutado correctamente |
| 6. Errores reales | Correcta | Repositorio local verificado | Ejecutado correctamente |
| 7. Integración de FreezeThaw | Correcta | Repositorio local verificado | Ejecutado correctamente |
| 8. Flujo JSON temporal | Correcta | Repositorio local verificado | Ejecutado correctamente |

Cada script se extrajo de este README, se analizó y compiló, se comprobaron sus
imports y se ejecutó en un proceso nuevo con directorio de trabajo temporal.
Se contrastaron las rutas de los módulos Orionis cargados con el repositorio
local. Todos produjeron su marcador esperado sin advertencias en stderr.

Las comprobaciones independientes de comportamiento ya confirmaron la guarda
de corrutina nativa, el error de corrutina consumida, el entero `0` ante
`KeyboardInterrupt`, el `runSync()` entre hilos, la comprobación de awaitables
basada en atributos, la continuidad del worker después de cancelar su espera,
la propagación de errores del cuerpo del contexto, la limpieza condicional,
la sustitución del bucle cacheado y la limitación de tipos en ejecución.

Las pruebas existentes se ejecutaron con `TestingEngine` y `TestRunner` de
Orionis y una aplicación con raíz temporal. Se comprobaron antes de ejecutar
los hashes de las copias sin cambios de
[tests/aio/test_loop.py](../../../tests/aio/test_loop.py) y
[tests/aio/test_package.py](../../../tests/aio/test_package.py). El resultado
fue **48 correctas, 0 fallidas, 0 con error, 0 omitidas**. Se desactivaron las
cachés de compilación y persistencia de resultados; se utilizó la implementación
local. Las pruebas simulan ramas de backend opcional con dobles; esto no
certifica el backend real de `uvloop`.

Distinciones neutrales entre código y documentación:

- `run()` declara `-> T`, pero su ruta de interrupción capturada devuelve el
  entero `0`.
- La docstring de `run()` asocia el error de bucle anidado con entradas de la
  biblioteca estándar; la implementación lo lanza explícitamente antes de
  entrar en ellas.
- `eventLoopContext()` afirma que no escapa ninguna excepción de la limpieza,
  pero la supresión se limita a `RuntimeError` y `asyncio.CancelledError`; los
  fallos de adquisición y del cuerpo no se capturan en general, y la limpieza
  puede esperar indefinidamente.
- Las docstrings de clase y de `runSync()` usan expresiones generales sobre
  seguridad entre hilos e interbloqueos; los mecanismos ejecutables son los
  bloqueos limitados y el puente bloqueante descritos, no garantías irrestrictas
  de concurrencia.

> ⚠️ No ejecutado en este entorno: los envíos recursivos de `runSync()` y las
> tareas de limpieza resistentes a la cancelación no se ejecutaron porque
> pueden esperar indefinidamente y el módulo no proporciona timeout.

Esta verificación no incluye integración con bases de datos o servicios de
correo reales, la suite de todo el framework ni certificación de plataformas
o versiones más allá del entorno indicado. No se reparó ningún fallo de
implementación ni se modificaron archivos fuente, pruebas, dependencias o
configuración como parte de esta tarea.
