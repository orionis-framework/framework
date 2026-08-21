# Tareas en Segundo Plano de Orionis (`orionis.background`)

> Envoltorio ligero e independiente del tipo de ejecución para ejecutar
> invocables — síncronos o asíncronos — después de que el flujo principal
> de una solicitud o proceso haya finalizado.
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.background` ofrece un pequeño conjunto de clases para diferir la
ejecución de uno o varios invocables hasta después de que el trabajo
"principal" haya terminado — el mismo concepto que usan los frameworks web
para ejecutar efectos secundarios (enviar un correo, escribir un registro
de auditoría, precalentar una caché) **después** de que una respuesta HTTP
ya fue enviada al cliente, sin hacer que el cliente espere a que ese efecto
secundario finalice.

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Qué problema resuelve](#qué-problema-resuelve)
3. [Referencia de API](#referencia-de-api)
   - [`IBackgroundTask`](#ibackgroundtask)
   - [`BackgroundTask`](#backgroundtask)
   - [`BackgroundTasks`](#backgroundtasks)
   - [`is_async_callable()`](#is_async_callable)
4. [Ejemplos de uso](#ejemplos-de-uso)
5. [Notas de diseño](#notas-de-diseño)
6. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
7. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita ningún paso de instalación adicional además del propio
framework:

```bash
pip install orionis
```

- **Python:** 3.14 o superior.
- **Dependencias:** ninguna más allá de la librería estándar de Python
  (`asyncio`, `functools`, `inspect`, `abc`).

## Qué problema resuelve

Algunas operaciones disparadas por una solicitud o un paso de un flujo de
trabajo no necesitan finalizar antes de que quien llama reciba un
resultado — por ejemplo, enviar un correo de confirmación, registrar un
evento de analítica o limpiar un archivo temporal. Ejecutarlas en línea
añadiría latencia innecesaria; ejecutarlas con llamadas improvisadas a
`asyncio.create_task` dispersas por el código es inconsistente y difícil de
probar. `orionis.background` estandariza este patrón con una API mínima:

- Envuelve **cualquier** invocable — síncrono o asíncrono — detrás de la
  misma interfaz (`BackgroundTask`), para que quien llama no tenga que
  distinguir entre ambos casos.
- Agrupa **varios** invocables en una sola unidad que los ejecuta en orden
  (`BackgroundTasks`), útil cuando más de un efecto secundario debe seguir
  a una operación.
- Expone un contrato común (`IBackgroundTask`) para que otras partes del
  framework (por ejemplo, `orionis.http.response`) puedan aceptar "algo con
  forma de tarea en segundo plano" sin depender de una implementación
  concreta.

## Referencia de API

### `IBackgroundTask`

```python
from orionis.background.contracts.task import IBackgroundTask
```

Clase base abstracta (`abc.ABC`) que define el contrato que toda
implementación de tarea en segundo plano debe cumplir.

| Miembro | Firma | Descripción |
| --- | --- | --- |
| `run` | `async def run(self) -> None` | Método corrutina abstracto. Las subclases concretas deben implementarlo para ejecutar la tarea. |

**Excepciones:** instanciar `IBackgroundTask` directamente lanza
`TypeError` (comportamiento estándar de `abc.ABC`) porque `run` es
abstracto.

---

### `BackgroundTask`

```python
from orionis.background.task import BackgroundTask
```

Envuelve un único invocable — síncrono o asíncrono — junto con los
argumentos posicionales y con nombre con los que debe llamarse, y lo expone
como una unidad de trabajo esperable (`awaitable`). Implementa
`IBackgroundTask`.

#### `BackgroundTask(func, *args, **kwargs)`

Constructor.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `func` | `Callable` | La función (o función corrutina) a ejecutar en segundo plano. |
| `*args` | `object` | Argumentos posicionales reenviados a `func` cuando la tarea se ejecuta. |
| `**kwargs` | `object` | Argumentos con nombre reenviados a `func` cuando la tarea se ejecuta. |

**Devuelve:** una nueva instancia de `BackgroundTask`. Si invocar `func`
produce un awaitable se detecta una sola vez, en el momento de la
construcción, mediante `is_async_callable`.

#### `await task()`

```python
async def __call__(self) -> None
```

Ejecuta el invocable envuelto:

- Si invocar `func` produce una corrutina, se espera directamente:
  `await func(*args, **kwargs)`.
- En caso contrario, `func` se invoca en el **executor por defecto** del
  bucle en ejecución mediante
  `loop.run_in_executor(None, functools.partial(func, *args, **kwargs))`,
  de modo que no bloquea el bucle de eventos.

**Devuelve:** `None`.

**Excepciones:** propaga cualquier excepción lanzada por `func`.

**Efectos secundarios:** ejecuta `func`, incluyendo cualquier efecto
secundario que `func` en sí misma tenga (E/S, registro de logs, mutación de
estado, etc.).

#### `await task.run()`

```python
async def run(self) -> None
```

Corrutina de conveniencia que simplemente hace `await self()`. Se provee
para satisfacer explícitamente el contrato `IBackgroundTask` (algunos
llamadores pueden preferir invocar `.run()` en lugar de invocar la
instancia directamente).

**Devuelve:** `None`.

**Excepciones:** las mismas que `__call__`.

---

### `BackgroundTasks`

```python
from orionis.background.tasks import BackgroundTasks
```

Gestiona una colección **ordenada** de instancias `BackgroundTask` y las
ejecuta una tras otra, en el orden en que fueron insertadas. Hereda de
`BackgroundTask` (de modo que una instancia de `BackgroundTasks` puede
usarse en cualquier lugar donde se espere un único `BackgroundTask` — por
ejemplo, como el argumento `background` de
`orionis.http.response.Response`), pero sobrescribe su constructor,
`__call__` y el almacenamiento interno para contener una lista de tareas en
lugar de un único invocable.

#### `BackgroundTasks(tasks=None)`

Constructor.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `tasks` | `Sequence[BackgroundTask] \| None`, opcional | Una secuencia opcional de instancias `BackgroundTask` ya construidas para inicializar la colección. |

**Devuelve:** una nueva instancia de `BackgroundTasks`. El argumento
`tasks` se convierte en una `list` y se expone como el atributo público
`self.tasks`. Si se omite o es un valor "falsy", `self.tasks` comienza como
una lista vacía.

#### `bt.addTask(func, *args, **kwargs)`

```python
def addTask(self, func: Callable, *args: object, **kwargs: object) -> None
```

Envuelve `func` (junto con sus argumentos) en un nuevo `BackgroundTask` y
lo añade a `self.tasks`.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `func` | `Callable` | La función (o función corrutina) a añadir como una nueva tarea en segundo plano. |
| `*args` | `object` | Argumentos posicionales reenviados a `func`. |
| `**kwargs` | `object` | Argumentos con nombre reenviados a `func`. |

**Devuelve:** `None`.

**Efectos secundarios:** muta `self.tasks` in situ (añade un elemento).

#### `await bt()`

```python
async def __call__(self) -> None
```

Ejecuta cada tarea actualmente en `self.tasks`, de forma **secuencial**, en
el orden en que fueron añadidas: `for task in self.tasks: await task()`.

**Devuelve:** `None`.

**Excepciones:** propaga la excepción lanzada por la tarea que falle; las
tareas programadas después de la que falla **no** se ejecutan (no hay un
try/except alrededor de cada iteración).

#### `await bt.run()`

```python
async def run(self) -> None
```

Heredada de `BackgroundTask`: hace `await self()`, lo que ejecuta todas las
tareas de la colección.

**Devuelve:** `None`.

**Excepciones:** las mismas que `__call__`.

---

### `is_async_callable()`

```python
from orionis.background.task import is_async_callable
```

Helper a nivel de módulo que usa `BackgroundTask` para decidir cómo debe
ejecutarse un invocable.

#### `is_async_callable(func)`

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `func` | `object` | Invocable a inspeccionar. Los objetos `functools.partial` se desenvuelven primero, y las instancias se inspeccionan a través de su `__call__`. |

**Devuelve:** `True` cuando invocar `func` produce una corrutina — funciones
corrutina, parciales de funciones corrutina y objetos cuyo `__call__` es una
corrutina (como `BackgroundTasks`) — y `False` en caso contrario, incluidos
los valores que no son invocables.

**Excepciones:** ninguna.

## Ejemplos de uso

### 1. Envolver una única función síncrona

```python
import asyncio
from orionis.background.task import BackgroundTask

def write_audit_log(user_id: int, action: str) -> None:
    print(f"[audit] user={user_id} action={action}")

async def main() -> None:
    task = BackgroundTask(write_audit_log, 42, action="login")
    await task()  # ejecuta write_audit_log en el executor por defecto del bucle

asyncio.run(main())
```

### 2. Envolver una función asíncrona

```python
import asyncio
from orionis.background.task import BackgroundTask

async def send_welcome_email(address: str) -> None:
    await asyncio.sleep(0.1)  # simula una llamada de E/S asíncrona
    print(f"correo de bienvenida enviado a {address}")

async def main() -> None:
    task = BackgroundTask(send_welcome_email, "user@example.com")
    await task.run()

asyncio.run(main())
```

### 3. Ejecutar varias tareas en secuencia

```python
import asyncio
from orionis.background.tasks import BackgroundTasks

def log_event(event: str) -> None:
    print(f"evento registrado: {event}")

async def notify_admin(message: str) -> None:
    await asyncio.sleep(0.05)
    print(f"administrador notificado: {message}")

async def main() -> None:
    tasks = BackgroundTasks()
    tasks.addTask(log_event, "user.created")
    tasks.addTask(notify_admin, "un nuevo usuario acaba de registrarse")

    await tasks()  # ejecuta log_event y luego notify_admin, en orden

asyncio.run(main())
```

### 4. Adjuntar una tarea en segundo plano a una respuesta HTTP

```python
from orionis.background.task import BackgroundTask
from orionis.http.response import JSONResponse

async def send_confirmation(order_id: int) -> None:
    print(f"confirmación enviada para el pedido {order_id}")

def make_response(order_id: int) -> JSONResponse:
    background = BackgroundTask(send_confirmation, order_id)
    return JSONResponse({"order_id": order_id}, background=background)

# El framework llama internamente a `await response.runBackground()` después
# de que el cuerpo de la respuesta ya fue enviado al cliente.
```

## Notas de diseño

Las siguientes notas describen decisiones de diseño **ya existentes** con
fines exclusivamente informativos — no son propuestas de cambio.

- **Un solo contrato, dos implementaciones.** `IBackgroundTask` (una
  `abc.ABC`) define la superficie mínima (`async def run(self) -> None`)
  que toda tarea en segundo plano debe exponer; tanto `BackgroundTask` como
  `BackgroundTasks` la satisfacen, de modo que el código que solo depende
  del contrato abstracto puede aceptar cualquiera de las dos de forma
  intercambiable.
- **Herencia por compatibilidad estructural.** `BackgroundTasks` extiende
  `BackgroundTask` en lugar de implementar únicamente `IBackgroundTask`
  directamente. Esto permite que una colección de tareas se pase a
  cualquier lugar donde se realice una comprobación
  `isinstance(x, BackgroundTask)` — en particular en
  `orionis.http.response`, cuyas respuestas aceptan un único parámetro
  `background: BackgroundTask | None`. `BackgroundTasks` sobrescribe por
  completo `__init__` y `__call__`, de modo que los atributos privados
  `func`/`args`/`kwargs` de la clase padre nunca se completan ni se usan en
  una instancia de `BackgroundTasks`.
- **Estado privado con "name mangling".** `BackgroundTask` almacena `func`,
  `args`, `kwargs` y el indicador de síncrono/asíncrono como atributos con
  doble guion bajo (`self.__func`, `self.__args`, `self.__kwargs`,
  `self.__is_async`), apoyándose en el "name mangling" de Python para
  mantenerlos privados a la clase, en lugar de exponerlos como parte de la
  API pública. Ambas clases y el contrato declaran `__slots__`, de modo que
  las instancias de tarea no tienen `__dict__`.
- **Patrón "invocable como tarea".** Ambas clases implementan `__call__`,
  de modo que una tarea (o una colección de tareas) puede invocarse
  directamente (`await task()`) o mediante el más descriptivo
  `await task.run()` — ambos hacen exactamente lo mismo.
- **La detección de síncrono/asíncrono ocurre una sola vez.** `BackgroundTask`
  inspecciona `func` con el helper de módulo `is_async_callable` en el
  momento de la construcción y almacena en caché el resultado
  (`self.__is_async`), en lugar de volver a comprobarlo en cada invocación.
  El helper desenvuelve los objetos `functools.partial` e inspecciona el
  `__call__` de las instancias, de modo que los objetos invocables que
  devuelven una corrutina — una colección `BackgroundTasks` entre ellos —
  se esperan en lugar de delegarse a un hilo y perderse.

## Consideraciones de rendimiento y concurrencia

Estas son notas informativas sobre el comportamiento existente, no
recomendaciones de optimización:

- Los invocables síncronos envueltos por `BackgroundTask` siempre se
  delegan al **executor por defecto** del bucle de eventos en ejecución
  mediante `loop.run_in_executor(None, ...)`. Esto requiere un bucle de
  eventos en ejecución (`asyncio.get_running_loop()` se llama
  internamente) — invocar un `BackgroundTask` que envuelve una función
  síncrona fuera de un bucle activo lanzará un `RuntimeError`.
- Dado que el executor por defecto se comparte con todo lo demás que lo use
  en el proceso, una tarea en segundo plano síncrona de larga duración
  puede ocupar uno de sus hilos trabajadores durante toda su duración.
- `BackgroundTasks.__call__` ejecuta sus tareas de forma **secuencial, no
  concurrente** — cada tarea se espera antes de que comience la siguiente.
  Si varias tareas necesitan ejecutarse en paralelo, deben programarse de
  forma independiente (por ejemplo, con `asyncio.gather` o
  `Loop.createTask` de `orionis.aio`) en lugar de a través de una única
  instancia de `BackgroundTasks`.
- Si una tarea dentro de una colección `BackgroundTasks` lanza una
  excepción, esta se propaga de inmediato y las tareas restantes de la
  lista **no** se ejecutan — no existe un aislamiento de errores integrado
  entre tareas.
- Los invocables asíncronos envueltos por `BackgroundTask` se ejecutan en
  el mismo bucle de eventos que los espera; siguen las reglas normales de
  multitarea cooperativa de `asyncio` (una corrutina asíncrona larga sin
  puntos `await` puede seguir retrasando a otras corrutinas del mismo
  bucle).

## Notas de compatibilidad

- **Versión mínima de Python:** 3.14.
- **Dependencias:** solo librería estándar — `abc`, `asyncio`, `functools`,
  `inspect`, `typing`. Este módulo no requiere paquetes de terceros.
- **Integración con el framework:** `orionis.http.response` depende de
  `BackgroundTask` (lo acepta como el parámetro `background` del
  constructor y expone `await response.runBackground()`), por lo que este
  módulo es una dependencia transitiva de la capa de respuestas HTTP.
