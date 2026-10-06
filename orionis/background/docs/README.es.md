# orionis.background

> Envuelve callables para ejecutarlos con await en el proceso y componer tareas ordenadas.

Versión en inglés: [README.md](README.md).

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Requisitos

No hay configuración, proveedor, extra de instalación ni servicio de workers
externos específicos de background. El módulo importa utilidades de la
biblioteca estándar y los símbolos `IBackgroundTask` y `Log` de Orionis; no
es independiente del framework. Consulta [../task.py](../task.py),
[../tasks.py](../tasks.py) y las versiones de dependencias en
[Notas de compatibilidad](#notas-de-compatibilidad).

- Ejecuta las entradas de corrutina en un contexto asyncio. La rama síncrona
  llama a `asyncio.get_running_loop()` y utiliza su executor por defecto.
  Cada script de abajo proporciona su propio contexto mediante `asyncio.run()`.
- Para producir registros de ejecución, inicializa y fija el logger. El
  arranque normal de la aplicación ejecuta `LoggerProvider.boot`; en una
  aplicación sin servidor ya creada, `await LoggerProvider(app).boot()`
  realiza la operación de pin de ese proveedor. `Application.create()` por
  sí solo no realiza esa operación. Evidencia:
  [../../logging/provider.py](../../logging/provider.py), `LoggerProvider.boot`;
  [../../foundation/application.py](../../foundation/application.py),
  `Application.create`, `Application.boot` y `Application.__onStartup`.

Sin un `Log` fijado, las llamadas sin await a `Log.info(...)` y
`Log.error(...)` realizadas por el módulo crean objetos de despacho diferido
y no escriben registros. La ejecución de tareas sigue funcionando. Esto se
comprobó en un proceso nuevo. Evidencia: [../task.py](../task.py),
`BackgroundTask.__call__`, y
[../../container/facades/meta.py](../../container/facades/meta.py),
`FacadeMeta.__getattr__` y `_FacadeDispatch`.

## Descripción funcional

`BackgroundTask` captura un callable y sus argumentos hasta ejecutarlo
explícitamente con `await task()` o `await task.run()`. `BackgroundTasks`
compone esas tareas en una colección secuencial y reutilizable. Una tarea
individual delega los registros de ejecución en la fachada `Log` de Orionis.

La construcción no programa ni invoca el callback. El módulo no contiene
despacho automático, cola persistente, scheduler, política de reintentos,
timeout ni mecanismo que garantice completar el trabajo al terminar el
proceso. Estas afirmaciones se refieren a este módulo, no a otros subsistemas
de Orionis. Evidencia: las implementaciones completas de
[../task.py](../task.py) y [../tasks.py](../tasks.py).

### Integración HTTP

`Response.__init__` acepta `background: BackgroundTask | None` y rechaza
explícitamente otros objetos con `TypeError`. Acepta `BackgroundTasks` porque
hereda de `BackgroundTask`; implementar únicamente `IBackgroundTask` no es
suficiente. `Response.runBackground()` espera `self.background()` cuando ese
atributo es truthy. No limpia el atributo ni lo marca como completado, por lo
que otra llamada vuelve a ejecutar el trabajo. Evidencia:
[../../http/responses.py](../../http/responses.py), `Response.__init__` y
`Response.runBackground`.

`ASGIResponseAdapter.send` y `RSGIResponseAdapter.send` esperan este hook
después de su ruta exitosa de entrega de respuesta, incluido HEAD. No lo
independizan mediante `asyncio.create_task`. La ruta con cuerpo materializado
de ASGI ya ha esperado el último mensaje del cuerpo; las rutas equivalentes
de RSGI y sus rutas de archivos ya han entregado la respuesta al protocolo.
Esto no demuestra que un cliente remoto haya recibido los bytes. Un fallo
previo de envío o limpieza impide alcanzar el hook; una ruta de desconexión
SSE puede retornar sin ejecutarlo. Evidencia:
[../../http/adapters/response/asgi.py](../../http/adapters/response/asgi.py),
`ASGIResponseAdapter.send` y `ASGIResponseAdapter.__sendHead`;
[../../http/adapters/response/rsgi.py](../../http/adapters/response/rsgi.py),
`RSGIResponseAdapter.send` y `RSGIResponseAdapter.__sendResponseStream`.

## Estructura del módulo

Se inspeccionaron recursivamente los cinco archivos Python de
`orionis/background`. Estas implementaciones no referencian recursos de
ejecución que no sean Python.

```text
orionis/background/
|-- __init__.py
|-- task.py
|-- tasks.py
|-- contracts/
|   |-- __init__.py
|   `-- task.py
`-- docs/
    |-- README.md
    |-- README.es.md
    `-- SKILL.md
```

| Fuente | Responsabilidad | Superficie pública documentada |
| --- | --- | --- |
| [../__init__.py](../__init__.py) | Reexportar las clases concretas. | `BackgroundTask`, `BackgroundTasks`, `__all__`. |
| [../task.py](../task.py) | Clasificar callables, ejecutar un callback y registrar su resultado. | `is_async_callable`, `BackgroundTask`, su constructor, `__call__` y `run`. |
| [../tasks.py](../tasks.py) | Almacenar y ejecutar una lista ordenada de tareas. | `BackgroundTasks`, su constructor, `tasks`, `addTask`, `__call__` y `run` heredado. |
| [../contracts/task.py](../contracts/task.py) | Declarar el contrato abstracto de ejecución. | `IBackgroundTask` y `run`. |
| [../contracts/__init__.py](../contracts/__init__.py) | Inicializador de paquete vacío. | Sin reexportaciones públicas explícitas. |

## Referencia de API

Los bloques de declaraciones de esta sección copian las firmas del código
fuente, incluidos decoradores y formato. Son fragmentos de referencia sin
cuerpos de método, no scripts ejecutables. Los scripts de
[Ejemplos de uso](#ejemplos-de-uso) son ejemplos ejecutables independientes.

### Importaciones y exportaciones públicas

| Símbolo | Import verificado | Definición |
| --- | --- | --- |
| `BackgroundTask` | `from orionis.background import BackgroundTask` o `from orionis.background.task import BackgroundTask` | [../task.py](../task.py) |
| `BackgroundTasks` | `from orionis.background import BackgroundTasks` o `from orionis.background.tasks import BackgroundTasks` | [../tasks.py](../tasks.py) |
| `IBackgroundTask` | `from orionis.background.contracts.task import IBackgroundTask` | [../contracts/task.py](../contracts/task.py) |
| `is_async_callable` | `from orionis.background.task import is_async_callable` | [../task.py](../task.py) |

La lista de exportaciones públicas del paquete se copia de
[../__init__.py](../__init__.py):

```python
__all__ = [
    "BackgroundTask",
    "BackgroundTasks",
]
```

El helper y el contrato se documentan porque tienen nombres públicos y
consumidores o pruebas directos existentes; no son reexportaciones del paquete
raíz. Las utilidades importadas como `asyncio`, `Any`, `Callable` y `Log` son
dependencias, no API adicionales de background. Los campos privados con name
mangling son estado de implementación; `__slots__` se trata en las
características de diseño. El inicializador vacío de contracts no reexporta
`IBackgroundTask`. Evidencia:
[../../../tests/background/test_package.py](../../../tests/background/test_package.py),
[../../../tests/background/test_task.py](../../../tests/background/test_task.py)
y [../../../tests/background/contracts/test_task.py](../../../tests/background/contracts/test_task.py).

### IBackgroundTask

Importa `orionis.background.contracts.task.IBackgroundTask`. Fuente:
[../contracts/task.py](../contracts/task.py).

```python
class IBackgroundTask(ABC):
```

```python
@abstractmethod
async def run(self) -> None:
```

Es una `abc.ABC` con `__slots__ = ()`, sin constructor explícito y con un único
miembro abstracto, `run`. La declaración no exige argumentos adicionales a
`self` y describe un resultado de `None` al esperarla. Su cuerpo contiene solo
una docstring; no hay ejecución de tareas predeterminada. Implementa el
comportamiento de ejecución en una subclase concreta.

La instanciación directa, o de una subclase que deje `run` abstracto, lanza el
`TypeError` de Python. Aquí no se implementa validación adicional de callbacks
ni de las firmas de métodos de las subclases. El contrato no declara
`__call__`, por lo que para un objeto que solo implemente el contrato se usa
`await implementation.run()`. El estado, los efectos y las excepciones de la
subclase concreta dependen de esa implementación. La restricción de tipos
concretos de HTTP se describe arriba. Evidencia:
[../../../tests/background/contracts/test_task.py](../../../tests/background/contracts/test_task.py),
`TestBackgroundTaskContract`.

### is_async_callable

Importa `orionis.background.task.is_async_callable`. Fuente:
[../task.py](../task.py), `is_async_callable`.

```python
def is_async_callable(func: object) -> bool:
```

| Elemento | Comportamiento implementado |
| --- | --- |
| `func: object` | Objeto a inspeccionar; no se invoca. |
| Inspección | Desenvuelve `functools.partial` repetidamente y aplica `inspect.iscoroutinefunction` al objeto resultante. En caso contrario, comprueba el atributo `__call__` de un objeto callable. |
| Resultado | `True` cuando tiene éxito alguna comprobación de función corrutina; `False` en caso contrario. Valores normales no invocables como `42` devuelven `False`. |
| Estado y efectos | Sin caché de módulo ni invocación del objeto. La consulta personalizada de atributos puede tener efectos o lanzar errores. |
| Excepciones | Sin `raise` explícito ni manejador de excepciones. Se propagan las excepciones de inspección de atributos; se comprobó una consulta de `__call__` que lanza. |

Una función síncrona normal que devuelva una corrutina se clasifica como
`False`. Una instancia callable asíncrona y un partial de ella se clasifican
como `True`. La rama de executor de `BackgroundTask` inspecciona por separado
el valor retornado, por lo que esta clasificación no determina si se espera
ese resultado. El helper no valida el resultado final ni la firma de
argumentos.

**Discrepancia de docstring:** la docstring del helper describe si invocar el
objeto produce un awaitable o una corrutina. La implementación solo
inspecciona si es una función corrutina; no invoca el objeto. Se comprobó esta
distinción con una factory síncrona de corrutinas. Evidencia existente:
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestIsAsyncCallable`.

### BackgroundTask

Importa `orionis.background.task.BackgroundTask`, también reexportado por
`orionis.background`. Fuente: [../task.py](../task.py), `BackgroundTask`.

```python
class BackgroundTask(IBackgroundTask):
```

#### Construcción

```python
def __init__(
    self,
    func: Callable,
    *args: object,
    **kwargs: object,
) -> None:
```

| Parámetro | Significado y restricciones |
| --- | --- |
| `func: Callable` | Callback obligatorio. La anotación no tiene parámetros de tipo; el constructor no comprueba que sea invocable. |
| `*args: object` | Argumentos posicionales capturados en una tupla. Al omitirlos se usa una tupla vacía. |
| `**kwargs: object` | Argumentos con nombre capturados en un diccionario. Al omitirlos se usa un diccionario vacío. |

El constructor retorna `None` y la construcción normal de la clase produce
la instancia de tarea. Retiene el callback y los valores de argumentos sin
copias profundas, y guarda `is_async_callable(func)` una vez para esta
instancia. El callback observa los cambios en objetos mutables referenciados
antes de una ejecución posterior. No invoca el callback ni obtiene un bucle
de eventos. Los errores de inspección pueden propagarse durante la
clasificación.

`BackgroundTask(42)` se acepta en la construcción pese a su anotación;
la ejecución posterior lanza `TypeError` al crear `functools.partial`.
Los argumentos ausentes o incompatibles del callback también se validan
solo al invocarlo realmente. Evidencia:
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestBackgroundTaskConstruction` y
`TestBackgroundTaskSynchronousExecution.testRejectsNonCallableTargetsWhenExecuted`.

#### Invocación

```python
async def __call__(self) -> None:
```

`await task()` realiza una nueva invocación:

1. Obtiene su nombre para logging de `func.__qualname__`, usando como fallback
   el nombre de clase del callable. Un partial normalmente usa `partial` como
   fallback. La consulta ocurre antes del bloque `try` de ejecución.
2. Si la clasificación guardada es asíncrona, espera directamente
   `func(*args, **kwargs)` en el bucle del llamador.
3. En caso contrario, vincula los argumentos mediante `functools.partial` y
   espera `loop.run_in_executor(None, bound)`. Si su resultado satisface
   `inspect.isawaitable(result)`, también lo espera en el bucle del llamador.
4. Descarta el resultado del callback, incluido el valor producido por un
   awaitable retornado, y devuelve `None` después del logging exitoso.

La rama de worker no itera automáticamente un generador normal o asíncrono.
Solo espera adicionalmente un resultado awaitable. No traslada recursos
ligados a un bucle que devuelva el callback. La comprobación adicional de
resultado solo existe en la rama de executor: los valores retornados por un
callback asíncrono esperado directamente se descartan sin un segundo await.

Dentro del bloque de ejecución, `except Exception` llama a `Log.error` y usa
`raise` sin argumentos. El bloque `else` llama a `Log.info`; la emisión real
depende de la configuración y el filtrado del logger fijado. Las plantillas
de mensaje de [../task.py](../task.py) son:

```text
Background task '<task_name>' failed: <error>
Background task '<task_name>' executed successfully.
```

Son plantillas, no una salida fija de ejecución. Los errores del callback y
del executor se propagan si el logging de error tiene éxito. El logging
también puede fallar: un error de `Log.error` interrumpe el `raise` sin
argumentos, y un error de `Log.info` escapa aunque el callback ya haya
completado su trabajo. Los errores de consulta de nombre ocurren fuera del
manejador. `asyncio.CancelledError` no se captura mediante
`except Exception`. Estos límites impiden dar una lista exhaustiva de
excepciones para callbacks y configuraciones de logging arbitrarios.

La tarea no guarda resultados ni se marca como consumida; cada invocación la
ejecuta de nuevo. `task()` produce una corrutina que su llamador debe esperar
o programar. La instancia no tiene `__await__`: `await task` no es esta API.
El wrapper no limpia automáticamente los recursos propiedad del callback.
Evidencia: [../task.py](../task.py), `BackgroundTask.__call__`, y
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestBackgroundTaskSynchronousExecution` y
`TestBackgroundTaskAsynchronousExecution`.

#### Ejecución explícita

```python
async def run(self) -> None:
```

`await task.run()` delega en `await self()` y devuelve `None`. Tiene los
mismos efectos y límites de excepciones que `__call__`, sin validación ni
manejo adicional de errores. Fuente: [../task.py](../task.py),
`BackgroundTask.run`; pruebas:
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestBackgroundTaskRunMethod`.

### BackgroundTasks

Importa `orionis.background.tasks.BackgroundTasks`, también reexportado por
`orionis.background`. Fuente: [../tasks.py](../tasks.py), `BackgroundTasks`.

```python
class BackgroundTasks(BackgroundTask):
```

#### Construcción y tasks

```python
def __init__(self, tasks: Sequence[BackgroundTask] | None = None) -> None:
```

`tasks` es una secuencia inicial opcional de objetos de tarea. El constructor
devuelve `None` e inicializa literalmente este atributo público y escribible:

```python
self.tasks: list[BackgroundTask] = list(tasks) if tasks else []
```

`None` y una entrada vacía o falsy crean una lista vacía nueva. Una entrada
truthy se materializa mediante `list(tasks)`: se copia la lista, no sus
objetos de tarea. Se propagan los errores de evaluación booleana o iteración.
La anotación no impone los tipos de elementos en runtime y las entradas no
se envuelven ni validan. Una entrada inválida falla después, cuando `__call__`
intenta invocarla y esperarla.

Mutar la lista de entrada después de construir no cambia la nueva lista;
mutar un objeto de tarea compartido sigue afectando a esa tarea. El atributo
público `tasks` puede consultarse, ampliarse, limpiarse o reasignarse sin
comprobación de setter. Los métodos posteriores operan sobre su valor actual.
Las entradas duplicadas se conservan y ejecutan por separado. El constructor
no llama al de la clase padre: los slots del callback de tarea individual
quedan sin inicializar y el método de ejecución sobrescrito no los utiliza.
Evidencia: [../tasks.py](../tasks.py), `BackgroundTasks.__init__`, y
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py),
`TestBackgroundTasksInitialization`.

#### Registro

```python
def addTask(
    self, func: Callable, *args: object, **kwargs: object,
) -> None:
```

`func`, `*args` y `**kwargs` tienen el mismo significado y restricciones que
en `BackgroundTask.__init__`. El método crea una nueva `BackgroundTask`
y la añade a `self.tasks`, retornando `None`, no la colección. No ejecuta ni
deduplica callbacks. Los errores de clasificación del nuevo wrapper se
propagan antes del append; también pueden propagarse errores de un
contenedor `tasks` que se haya reemplazado.

Puede registrarse como callable una instancia asíncrona, otra tarea u otra
`BackgroundTasks`. Registrar una colección interna mediante `addTask(inner)`
añade un wrapper externo, por lo que ese wrapper también produce su propia
llamada de logging. Una colección interna suministrada directamente al
constructor no añade ese wrapper. Evidencia: [../tasks.py](../tasks.py),
`BackgroundTasks.addTask`, y
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py),
`TestBackgroundTasksAddTask` y
`TestBackgroundTasksExecution.testRunsNestedCollectionsRegisteredWithAddTask`.

#### Invocación y run heredado

```python
async def __call__(self) -> None:
```

La implementación recorre una lista viva: `for task in self.tasks:
await task()`. Cada entrada termina antes de iniciar la siguiente; devuelve
`None` cuando todas completan. Una colección vacía no realiza trabajo. No
tiene snapshot, manejador de excepciones por entrada, llamada de logging de
colección ni indicador de finalización. La primera excepción interrumpe la
secuencia; no se invocan las tareas posteriores en esa ejecución y la lista
almacenada permanece intacta.

Añadir o retirar elementos durante la ejecución puede cambiar las entradas
que visita el iterador actual de la lista. Un probe confirmó que un append
durante el primer callback se visita en la misma ejecución. Las ejecuciones
posteriores comienzan desde el principio de la lista actual, incluidas las
tareas ya completadas en una ejecución previa fallida. Las colecciones
anidadas se ejecutan en profundidad según su orden almacenado; no hay
detector de ciclos.

`run` se hereda sin cambios de `BackgroundTask`: su firma literal es
`async def run(self) -> None:` como se muestra arriba, y `await self()`
despacha al `__call__` de esta colección. Tiene el mismo orden, resultados
y comportamiento de excepciones. Evidencia: [../tasks.py](../tasks.py),
`BackgroundTasks.__call__`; [../task.py](../task.py), `BackgroundTask.run`;
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py),
`TestBackgroundTasksExecution` y
`TestBackgroundTasksSubstitutability.testInheritsTheRunEntryPoint`.

## Ejemplos de uso

Ejecuta cada bloque como script independiente con el framework instalado y
Python 3.14+. Cada uno proporciona su contexto asyncio y no usa servicios
externos. Estos ejemplos deliberadamente no arrancan una aplicación ni fijan
`Log`, por lo que verifican los efectos de las tareas, no sus registros de
ejecución. El logging configurado se comprobó por separado con una aplicación
aislada durante las pruebas nativas.

### 1. Ejecutar y reutilizar una tarea síncrona

La construcción es diferida, el callback se ejecuta en un hilo worker y
ambas entradas descartan su valor retornado. Reutilizar la instancia vuelve
a invocarlo.

```python
import asyncio
import threading
from orionis.background import BackgroundTask

observed: list[tuple[int, int]] = []

def record(value: int) -> str:
    """Record a value and the executing thread."""
    observed.append((value, threading.get_ident()))
    return "discarded"

async def main() -> None:
    """Execute the same task through both entry points."""
    loop_thread = threading.get_ident()
    task = BackgroundTask(record, 7)
    assert observed == []
    assert await task() is None
    assert await task.run() is None
    assert [value for value, thread_id in observed] == [7, 7]
    assert all(thread_id != loop_thread for value, thread_id in observed)

asyncio.run(main())
```

### 2. Detectar y esperar una instancia callable asíncrona

El helper inspecciona a través de un partial y reconoce el `__call__`
asíncrono de la instancia. El callback termina antes de que `run` retorne.

```python
import asyncio
from functools import partial
from orionis.background import BackgroundTask
from orionis.background.task import is_async_callable

class Recorder:
    """Collect values through an async call method."""

    __slots__ = ("values",)

    def __init__(self) -> None:
        """Initialize the recorded values."""
        self.values: list[str] = []

    async def __call__(self, value: str) -> None:
        """Record one supplied value."""
        self.values.append(value)

async def main() -> None:
    """Classify and execute a partially bound callable instance."""
    recorder = Recorder()
    bound = partial(recorder, "completed")
    assert is_async_callable(bound)
    assert await BackgroundTask(bound).run() is None
    assert recorder.values == ["completed"]

asyncio.run(main())
```

### 3. Manejar el fallo de un callback en una colección

El `ValueError` del callback llega al llamador; la tarea posterior no se
ejecuta. La colección sigue conteniendo sus tres entradas.

```python
import asyncio
from orionis.background import BackgroundTask, BackgroundTasks

events: list[str] = []

def record(value: str) -> None:
    """Append one execution marker."""
    events.append(value)

def reject() -> None:
    """Raise a deliberate callback failure."""
    error_msg = "task rejected"
    raise ValueError(error_msg)

async def main() -> None:
    """Observe the failure without losing the stored task list."""
    tasks = BackgroundTasks([BackgroundTask(record, "before")])
    tasks.addTask(reject)
    tasks.addTask(record, "after")
    try:
        await tasks.run()
    except ValueError as error:
        assert str(error) == "task rejected"
    else:
        error_msg = "Expected the callback failure"
        raise AssertionError(error_msg)
    assert events == ["before"]
    assert len(tasks.tasks) == 3

asyncio.run(main())
```

### 4. Ejecutar después de una respuesta ASGI en memoria

Usa la respuesta y los adaptadores reales con un canal send ASGI en memoria,
no un servidor ni un socket. Comprueba el orden después del mensaje del cuerpo
materializado y demuestra que un segundo `runBackground()` explícito repite
el trabajo.

```python
import asyncio
from orionis.background import BackgroundTask
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.responses import Response

events: list[str] = []
messages: list[dict[str, object]] = []

async def receive() -> dict[str, object]:
    """Supply a complete empty request message."""
    return {"type": "http.request", "body": b"", "more_body": False}

async def send(message: dict[str, object]) -> None:
    """Record an ASGI response message."""
    messages.append(message)
    events.append(str(message["type"]))

async def after_send() -> None:
    """Record background execution after the final body message."""
    assert messages[-1]["type"] == "http.response.body"
    assert messages[-1]["more_body"] is False
    events.append("background")

async def main() -> None:
    """Send a buffered response through the real ASGI adapter."""
    adapter = ASGITransportAdapter({
        "type": "http", "method": "GET", "headers": [],
    })
    response = Response("accepted", background=BackgroundTask(after_send))
    assert events == []
    await ASGIResponseAdapter().send(adapter, response, receive, send)
    assert events == ["http.response.start", "http.response.body", "background"]
    assert messages[0]["status"] == 200
    assert messages[1]["body"] == b"accepted"
    await response.runBackground()
    assert events[-2:] == ["background", "background"]

asyncio.run(main())
```

### 5. Componer un flujo local de archivos y una factory de awaitables

Se copia la lista inicial, se registra una colección interna como callable
y una factory síncrona devuelve una corrutina que se espera en el bucle.
Cada ejecución repite el flujo; el clear explícito final lo convierte en una
operación sin trabajo. El directorio temporal se elimina solo después de
completar todo el trabajo esperado.

```python
import asyncio
from collections.abc import Coroutine
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.background import BackgroundTask, BackgroundTasks
from orionis.background.contracts.task import IBackgroundTask
from orionis.background.task import is_async_callable

def write_report(path: Path, content: str) -> None:
    """Write the local report from a worker thread."""
    path.write_text(content, encoding="utf-8")

def read_report(path: Path, events: list[str]) -> None:
    """Record the report contents from a worker thread."""
    events.append(path.read_text(encoding="utf-8"))

async def mark_ready(events: list[str]) -> None:
    """Record completion on the awaiting event loop."""
    events.append("ready")

def make_completion(events: list[str]) -> Coroutine[object, object, None]:
    """Return a coroutine without being a coroutine function."""
    return mark_ready(events)

async def execute(task: IBackgroundTask) -> None:
    """Execute any implementation through the abstract contract."""
    await task.run()

async def main() -> None:
    """Complete and replay an isolated mixed task workflow."""
    with TemporaryDirectory(prefix="orionis-background-example-") as directory:
        path = Path(directory) / "report.txt"
        events: list[str] = []
        seed = [BackgroundTask(write_report, path, "report")]
        inner = BackgroundTasks(seed)
        seed.clear()
        assert len(inner.tasks) == 1
        outer = BackgroundTasks()
        outer.addTask(inner)
        outer.addTask(partial(read_report, path), events)
        outer.addTask(make_completion, events)
        assert is_async_callable(inner)
        assert not is_async_callable(make_completion)
        await execute(outer)
        assert events == ["report", "ready"]
        await outer.run()
        assert events == ["report", "ready", "report", "ready"]
        outer.tasks.clear()
        assert await outer.run() is None

asyncio.run(main())
```

### 6. Implementar el contrato sin una interfaz callable

La ABC solo exige `run`. Una implementación exclusiva del contrato puede
ejecutarse directamente o envolver su método ligado `run` en `BackgroundTask`.
El objeto por sí solo no es un valor válido de `Response(background=...)`.

```python
import asyncio
from orionis.background import BackgroundTask
from orionis.background.contracts.task import IBackgroundTask

class Checkpoint(IBackgroundTask):
    """Count executions through the abstract contract."""

    __slots__ = ("executions",)

    def __init__(self) -> None:
        """Initialize the execution counter."""
        self.executions = 0

    async def run(self) -> None:
        """Record one completed execution."""
        self.executions += 1

async def main() -> None:
    """Execute a contract-only object and its wrapped method."""
    checkpoint = Checkpoint()
    assert not callable(checkpoint)
    await checkpoint.run()
    await BackgroundTask(checkpoint.run).run()
    assert checkpoint.executions == 2
    try:
        IBackgroundTask()
    except TypeError:
        pass
    else:
        error_msg = "Expected the abstract-construction error"
        raise AssertionError(error_msg)

asyncio.run(main())
```

## Características de diseño

| Mecanismo observado | Consecuencia para quien consume la API | Evidencia |
| --- | --- | --- |
| `IBackgroundTask(ABC)` con una corrutina abstracta | Quien consume el contrato llama a `run`; HTTP utiliza una comprobación más restrictiva de tipo concreto. | [../contracts/task.py](../contracts/task.py); [../../http/responses.py](../../http/responses.py) |
| `BackgroundTasks(BackgroundTask)` con constructor e invocación sobrescritos | Las colecciones pasan la comprobación `isinstance` de HTTP y reutilizan el dispatcher `run` heredado. | [../tasks.py](../tasks.py); [../task.py](../task.py) |
| Slots en la ABC y en ambas clases concretas | Las instancias suministradas no tienen `__dict__` de instancia; las subclases arbitrarias deben elegir su propia disposición. | `IBackgroundTask.__slots__`, `BackgroundTask.__slots__`, `BackgroundTasks.__slots__` en las fuentes anteriores |
| Clasificación de corrutina guardada por instancia | La clasificación queda fijada al construir; el resultado del executor se inspecciona en cada ejecución de la rama síncrona. | [../task.py](../task.py), `BackgroundTask.__init__` y `__call__` |
| Referencias de argumentos capturadas y lista pública mutable | Los argumentos mutables y objetos de tarea compartidos siguen vivos; la construcción de la colección solo copia la lista externa. | [../task.py](../task.py); [../tasks.py](../tasks.py) |

No hay caché de tareas o resultados a nivel de módulo, constructor generado
por dataclass, registro singleton de tareas ni interfaz de colección basada
en generadores. El `Log` importado utiliza el estado de su fachada; no es un
logger por tarea. Evidencia: los cinco archivos del módulo y
[../../container/facades/facade.py](../../container/facades/facade.py),
`Facade._pinned_instance`.

## Rendimiento y concurrencia

- El registro retiene las referencias del callback y sus argumentos hasta
  liberar la propia tarea. Una colección con entradas iniciales materializa
  una nueva lista y retiene los objetos de tarea; la ejecución no la limpia
  ni vuelve a copiarla.
- Cada invocación de la rama síncrona crea un nuevo `functools.partial` y
  utiliza el executor por defecto del bucle, no un pool dedicado a background.
  Un callback en ejecución ocupa un worker hasta retornar. Cualquier awaitable
  retornado se espera después en el bucle del llamador.
- Los callbacks asíncronos se ejecutan directamente en ese bucle. Sus
  operaciones bloqueantes pueden bloquearlo; declarar `async def` no garantiza
  una ejecución no bloqueante.
- `Log.info` y `Log.error` se llaman síncronamente desde el bucle que espera.
  Con un logger del framework fijado, la inicialización y las operaciones
  de handlers de archivo pueden realizar E/S síncrona. Evidencia:
  [../../logging/logger.py](../../logging/logger.py), `Logger.info`,
  `Logger.error` y `Logger.__initializeLogger`.
- Una colección espera sus entradas secuencialmente. Las llamadas concurrentes
  separadas sobre una misma tarea o colección no se serializan y pueden invocar
  el mismo callback varias veces en paralelo. El módulo no contiene locks de
  ejecución ni de lista.
- La colección recorre su lista viva. Una mutación a través de un await del
  callback puede alterar la ejecución actual, no solo la siguiente. No se
  implementa comportamiento exactly-once ni aislamiento mediante snapshot.
- La cancelación se propaga a través de los awaits; aquí no hay shielding,
  timeout, reintento ni protocolo de detención de workers. Cancelar a quien
  espera no detiene forzosamente un callback de executor ya iniciado. Un
  probe con worker controlado mediante una señal de liberación confirmó la
  distinción.
- El wrapper usa `run_in_executor`, no `asyncio.to_thread`, y no copia
  explícitamente el contexto de `contextvars`. No deduzcas propagación de
  contexto ni gestión de duración de recursos de la palabra "background".

Salvo que se enlace por separado, la evidencia de estos puntos es
[../task.py](../task.py), `BackgroundTask.__init__` y `__call__`, y
[../tasks.py](../tasks.py), `BackgroundTasks.__init__`, `addTask` y `__call__`.
La ejecución repetida y el fallo secuencial también se cubren en
[../../../tests/background/test_task.py](../../../tests/background/test_task.py)
y [../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py).

> ⚠️ No especificado en el código fuente: un contrato de seguridad para
> reutilización entre hilos, mutación concurrente o thread safety de callbacks
> arbitrarios. La ausencia observable de serialización descrita arriba no
> constituye una garantía general de thread safety.

## Notas de compatibilidad

- Mínimo del proyecto: Python `>=3.14`, declarado en
  [../../../pyproject.toml](../../../pyproject.toml). Esta tarea tiene como
  objetivo 3.14+; se validó con **CPython 3.14.6 en Windows**, utilizando el
  virtualenv del repositorio. Estas ejecuciones no certifican otras versiones
  de Python.
- Los módulos concretos usan `from __future__ import annotations`, sintaxis de
  uniones e imports de `Callable`/`Sequence` bajo `TYPE_CHECKING`. La ejecución
  no necesita esos imports exclusivos de anotaciones. Evaluar
  `typing.get_type_hints(BackgroundTask.__init__)` en el módulo inspeccionado
  lanzó `NameError` por `Callable`; no confundas ese problema de introspección
  con un fallo de ejecución de tareas. Evidencia: [../task.py](../task.py) y
  [../tasks.py](../tasks.py).
- No hay imports directos de terceros en estos cinco archivos. `Log` es una
  dependencia interna en runtime. Su infraestructura de logging y la
  integración HTTP usan dependencias del framework; no son extras opcionales
  de background. El módulo no elige una implementación de bucle asyncio.

Las versiones declaradas y resueltas relevantes son distintas:

| Dependencia y función | Restricción del manifiesto | Resolución del lockfile | Entorno de validación |
| --- | --- | --- | --- |
| `rich`, salida de las pruebas nativas | `>=15.0.0,<16.0` | `15.0.0` | `15.0.0` |
| `pendulum`, fechas y arranque del framework | `>=3.2.0,<4.0` | `3.2.0` | `3.2.0` |
| `msgspec`, infraestructura de respuestas | `>=0.21.1` | `0.22.0` | `0.22.0` |
| `granian`, servidor HTTP del framework | `>=2.8.3,<3.0` | `2.8.4` | `2.8.4` |
| `ruff`, comprobación de lint exclusiva de desarrollo | `>=0.16.8` | `0.16.9` | `0.16.9` |

Evidencia: [../../../pyproject.toml](../../../pyproject.toml), `dependencies`
y `dependency-groups.dev`; [../../../uv.lock](../../../uv.lock), las entradas
de paquetes nombradas; las versiones instaladas se consultaron durante la
validación. Las resoluciones del lockfile no son mínimos soportados. El
ejemplo ASGI no arranca Granian ni ejercita su protocolo de red.

## Verificación y limitaciones

### Cobertura y evidencia

El inventario cubre cinco archivos fuente, tres clases públicas, un helper
público, siete declaraciones explícitas de métodos, el atributo `tasks`, las
dos reexportaciones raíz y `__all__`. Todos se representan arriba. Las
utilidades importadas y los campos privados de almacenamiento se excluyen de
la API pública por los motivos de
[Importaciones y exportaciones públicas](#importaciones-y-exportaciones-públicas).

Se inspeccionaron los cuatro archivos de pruebas existentes:
[../../../tests/background/test_package.py](../../../tests/background/test_package.py),
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py)
y [../../../tests/background/contracts/test_task.py](../../../tests/background/contracts/test_task.py).
El descubrimiento nativo con `TestingEngine` y la ejecución con `TestRunner`
completaron **77/77 pruebas correctamente**, sin fallos crudos, errores crudos
ni omisiones. La aplicación se creó en un directorio temporal,
`LoggerProvider.boot()` inicializó la fachada de logging y no se activó la
caché de resultados. No fue una ejecución del bootstrap Reactor configurado
del checkout ni una suite de todo el framework.

Los probes locales adicionales comprobaron la clasificación de corrutinas,
la procedencia de imports locales, el fallo al evaluar anotaciones, la
separación worker/bucle de una factory síncrona de corrutinas, el rechazo
diferido de un no callable, el append sobre una lista viva, las llamadas
concurrentes no sincronizadas y la cancelación de quien espera mientras su
callback de executor continuaba. Otras comprobaciones confirmaron el await
único de un callback asíncrono directo, el logger sin pin después de
`Application.create()` y los fallos de logging después del éxito del callback
o durante la propagación de errores. Son casos concretos comprobados, no
garantías universales de callbacks ni mediciones de benchmarks.

### Resultados de ejemplos

| Ejemplo | Sintaxis | Imports locales | Ejecución |
| --- | --- | --- | --- |
| 1. Tarea síncrona | Correcta | Correctos | Ejecutado correctamente. |
| 2. Instancia callable asíncrona | Correcta | Correctos | Ejecutado correctamente. |
| 3. Fallo de callback | Correcta | Correctos | Ejecutado correctamente. |
| 4. Respuesta ASGI | Correcta | Correctos | Ejecutado correctamente. |
| 5. Flujo de archivos | Correcta | Correctos | Ejecutado correctamente. |
| 6. Contrato abstracto | Correcta | Correctos | Ejecutado correctamente. |

Se compararon literalmente las once declaraciones, la lista de exportaciones
y la inicialización del atributo con las fuentes locales. Los seis scripts
se extrajeron de este README, se compilaron, se comprobaron sus imports locales
por separado y se ejecutaron con directorios de trabajo temporales
independientes. No se emitieron warnings.

Ambos README tienen 32 encabezados equivalentes, 21 bloques idénticos y 78
enlaces locales válidos cada uno. Los 14 enlaces del skill y su frontmatter
YAML de dos campos se comprobaron independientemente; su nombre derivado es
`orionis-background`. Las restricciones del manifiesto y las resoluciones del
lockfile se contrastaron mediante parsing TOML. Ruff pasó para el módulo y
sus pruebas existentes, sin correcciones ni escrituras de caché. Los scripts,
informes y recursos de validación se mantienen fuera del repositorio.

### Límites restantes

La discrepancia de docstring del helper y el comportamiento de evaluación de
anotaciones se documentan arriba sin cambiar la implementación. Las
excepciones específicas de callbacks y sus contratos de recursos no pueden
reducirse a una lista exhaustiva mediante este wrapper. Los resultados de
pruebas no implican ejecución durable ni entrega exactly-once.

El validador de skills de VS Code reporta que el nombre del skill difiere de
su carpeta padre `docs` y trata enlaces `README.md#section` como rutas de
archivo literales. El parseo independiente de YAML y las comprobaciones de
destinos y anclas Markdown pasaron. Se conservan el nombre, el directorio y
los enlaces de sección válidos solicitados: este punto de entrada no afirma
estar registrado automáticamente en la plataforma.

> ⚠️ No ejecutado en este entorno: rutas de transporte RSGI/SSE, transmisión
> real con Granian o por red, ejecución Linux o free-threaded y otras versiones
> de Python. La ejecución de transporte se limitó a ASGI con cuerpo
> materializado; se validó con CPython 3.14.6 en Windows y recursos locales o
> en memoria aislados.
