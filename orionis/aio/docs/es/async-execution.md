# Conectar código síncrono y asíncrono

`Loop` proporciona gestión de event loops, programación de tareas y despacho de callables. Se importa directamente: no requiere una aplicación Orionis, un provider, un archivo de configuración ni un servicio externo.

## Requisitos

- Python 3.14 o posterior, según declara el proyecto.
- Una instalación normal de Orionis; no existe un extra separado de `aio`.
- Fuera de Windows, Orionis utiliza `uvloop` cuando puede importarse. En Windows selecciona `asyncio.ProactorEventLoop` cuando está disponible. En los demás casos utiliza la factoría estándar de asyncio.

## Elegir la operación adecuada

| Situación | Operación | Comportamiento |
|---|---|---|
| Script o CLI sin loop activo | `Loop.run(main())` | Posee un loop y devuelve el resultado de la corrutina. |
| Dentro de una función async | `await main()` | Utiliza el loop y los recursos actuales. |
| Callable sync o async | `await Loop.execute(callback, ...)` | Ejecuta lo síncrono en un worker y espera los resultados asíncronos. |
| Trabajo concurrente en el loop actual | `task = Loop.createTask(work())` | Programa inmediatamente; espera `task` para obtener el resultado. |
| API síncrona sin loop activo | `Loop.runSync(work())` | Aplica la misma propiedad y validación que `run`. |
| Bloque síncrono que requiere un loop gestionado | `with Loop.eventLoopContext() as loop:` | Toma prestado un loop existente o posee uno nuevo. |

`run` y `runSync` rechazan llamadas desde un hilo que ya ejecuta un event loop. No trasladan esa corrutina a un worker privado. Una corrutina rechazada sigue perteneciendo al llamador: debe esperarla o cerrarla.

## Iniciar un script y desplazar trabajo bloqueante

```python
from orionis.aio import Loop


def blocking_label(value: int) -> str:
    return f"job-{value}"


async def main() -> str:
    label = await Loop.execute(blocking_label, 7)
    return label.upper()


print(Loop.run(main()))  # JOB-7
```

`run` crea y registra un loop propio antes de iniciar la corrutina. Al salir, `asyncio.Runner` cancela y drena tareas pendientes, finaliza generadores asíncronos, cierra el ejecutor predeterminado y cierra ese loop. Restaura un loop previamente registrado que siga abierto; no vuelve a registrar uno que se haya cerrado. Los errores de la corrutina y `KeyboardInterrupt` se propagan al llamador.

`execute` acepta un callable, no un objeto corrutina ya creado. Espera las funciones corrutina en el loop del llamador. Los demás callables se ejecutan en el ejecutor predeterminado de ese loop con una copia del contexto `contextvars` del llamador. Los cambios realizados a variables de contexto dentro del worker no alteran el contexto del llamador. Si un callable síncrono devuelve un awaitable, incluida una corrutina basada en generador, el resultado se espera en el loop del llamador. Los generadores ordinarios se devuelven como valores sin esperarlos.

Los argumentos con nombre se transmiten sin cambios:

```python
from orionis.aio import Loop


def sync_join(*, left: str, right: str) -> str:
    return f"{left}:{right}"


async def async_join(*, left: str, right: str) -> str:
    return f"{left}/{right}"


async def main() -> tuple[str, str]:
    first = await Loop.execute(sync_join, left="a", right="b")
    second = await Loop.execute(async_join, left="a", right="b")
    return first, second


print(Loop.run(main()))  # ('a:b', 'a/b')
```

Cancelar la tarea que espera no puede detener por la fuerza un callable síncrono que ya se ejecuta en un worker. En particular, la cancelación no demuestra que un envío SMTP o una operación de archivos no se hayan completado. Los resultados awaitable deben pertenecer al loop del llamador; no devuelvas futures pendientes ligados a otro loop.

El trabajo en cola comprueba la cancelación antes de invocar su callable. Cuando termina un callable ya iniciado, un resultado corrutina abandonado se cierra y se solicita la cancelación de un future abandonado en su loop propietario cuando ese loop permanece abierto. También se observa la excepción de un future que falla antes de poder cancelarlo. Una excepción tardía del worker o de la limpieza se captura en el runtime de fallos de Orionis activo, o llega al manejador de excepciones del loop cuando no hay un runtime activo.

## Programar y observar una tarea

`createTask` es síncrono. Conserva la tarea devuelta y espérala para recibir su resultado o excepción:

```python
from orionis.aio import Loop


async def fetch_total() -> int:
    return 42


async def main() -> tuple[str, int]:
    task = Loop.createTask(fetch_total(), name="fetch-total")
    return task.get_name(), await task


print(Loop.run(main()))  # ('fetch-total', 42)
```

La tarea captura el contexto presente al crearla y queda programada sin un `await` adicional sobre la factoría. Cuando hay un runtime de fallos de Orionis activo, la programación delega en su supervisión de tareas. En los demás casos delega en `asyncio.create_task`. Crear una tarea no proporciona persistencia ni reintentos.

## Poseer o tomar prestado un loop

El registro de asyncio para el hilo llamador es la fuente de verdad. `getEventLoop()` devuelve primero un loop activo, después uno registrado y abierto, o crea y registra uno nuevo. Cuando crea el loop, el llamador es su propietario y debe cerrarlo.

`eventLoopContext()` tiene dos ciclos de vida distintos:

- Si existe un loop registrado abierto o activo, lo toma prestado. No cancela sus tareas ni lo cierra, incluso si el bloque lanza una excepción.
- Si no existe un loop registrado abierto, crea uno y utiliza la limpieza de Runner al salir. Los contextos anidados toman prestado el loop externo y dejan su limpieza al propietario.

Para obtener limpieza automática, entra directamente al contexto antes de adquirir un loop:

```python
from orionis.aio import Loop


async def calculate() -> int:
    return 42


with Loop.eventLoopContext() as loop:
    result = loop.run_until_complete(calculate())

print(result, loop.is_closed())  # 42 True
```

Este ejemplo corresponde a un hilo síncrono sin loop registrado. Si llamas primero a `getEventLoop()`, un contexto posterior toma prestado ese loop y no adquiere su propiedad. No cierres manualmente un loop gestionado ni lo dejes ejecutándose cuando salga su contexto: ambas situaciones provocan `RuntimeError` en lugar de omitir silenciosamente la limpieza.

## Adaptar una corrutina a una API síncrona

```python
from orionis.aio import Loop


async def lookup(code: str) -> str:
    return code.upper()


print(Loop.runSync(lookup("orionis")))  # ORIONIS
```

`runSync` es un punto de entrada síncrono directo en el hilo llamador. Dentro de código async, utiliza `await lookup(...)`. No mantiene un ejecutor compartido y los llamadores síncronos independientes no pasan por un único worker. Los recursos ligados a otro event loop no se pueden trasladar simplemente usando este puente.

## Configuración e integración

La selección de factoría se conserva a nivel de clase; la detección de uvloop utiliza un lock. El paquete no consume claves de configuración ni variables de entorno de Orionis, ni ofrece un reemplazo público de la factoría. El registro de loops sigue perteneciendo a cada hilo mediante asyncio; Orionis no mantiene una segunda caché de loops por hilo.

Entre sus consumidores directos están el punto de entrada `reactor` y la CLI (`run`), la composición y los transportes de correo (`execute`), y la supervisión del runtime de fallos (`createTask`). Importar `orionis.aio` no crea por sí solo un loop, ejecutor ni aplicación.

## API y errores

| Firma | Valor devuelto y restricciones |
|---|---|
| `Loop.getEventLoop() -> asyncio.AbstractEventLoop` | Devuelve un loop abierto; el llamador posee únicamente un loop creado por esta llamada. |
| `Loop.run(coro: Coroutine[Any, Any, T]) -> T` | Acepta un objeto corrutina nativo; rechaza un loop activo en este hilo. |
| `await Loop.execute(func, /, *args, **kwargs) -> Any` | Acepta un callable y conserva sus resultados y excepciones durante el despacho. |
| `Loop.eventLoopContext()` | Entrega un loop prestado o propio con el ciclo de vida descrito arriba. |
| `Loop.isLoopRunning() -> bool` | Indica si este hilo está ejecutando un loop; un registro inactivo no basta. |
| `Loop.createTask(coro, *, name=None) -> asyncio.Task[T]` | Requiere un loop activo y devuelve inmediatamente la tarea programada. |
| `Loop.runSync(coro: Coroutine[Any, Any, T]) -> T` | Delega en `run` sin un ejecutor privado. |

`run` y `runSync` lanzan `TypeError("A coroutine object is required")` para funciones corrutina, valores simples y awaitables generales que no sean objetos corrutina nativos. Lanzan `RuntimeError` si se llaman desde un loop activo. `execute` lanza `TypeError("The provided object is not callable")` antes de despachar un objeto no invocable. Las excepciones del código ejecutado se propagan; ningún error se convierte en un retorno exitoso.

La capacidad y el cierre de los workers pertenecen al ejecutor predeterminado del loop. Conservar la factoría evita repetir la detección, pero no establece una garantía de latencia ni rendimiento. Las tareas cooperativas deben ceder el control para que avance otro trabajo en el mismo loop.

## Referencia de implementación

| Ruta | Responsabilidad |
|---|---|
| `__init__.py` | Expone `Loop` mediante las exportaciones diferidas del paquete. |
| `loop.py` | Selecciona factorías, gestiona propiedad, despacha callables y programa tareas. |

[Índice](README.md) · [background](../../../background/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)
