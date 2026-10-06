# orionis.background

> `orionis.background` ejecuta callables síncronos o asíncronos después de una respuesta HTTP de Orionis y admite colecciones ordenadas de tareas.

## Descripción general

Utiliza este módulo para trabajo breve posterior que pertenezca al proceso actual pero deba ocurrir después de enviar el cuerpo de una respuesta, como despachar una notificación o registrar actividad secundaria. `BackgroundTask` envuelve un callable; `BackgroundTasks` almacena varios wrappers y los ejecuta secuencialmente.

Ambos tipos pueden esperarse mediante su `__call__` async y exponen `run()`. Los callables síncronos se mueven al ejecutor predeterminado del loop activo, mientras los async permanecen en el loop. Los adaptadores de respuesta de Orionis invocan `response.runBackground()` después de una entrega ASGI o RSGI correcta.

Esto no es una cola durable: las tareas solo viven en memoria, se ejecutan en el proceso servidor y no sobreviven a su terminación.

## Requisitos

- Python 3.14 o posterior.
- Una instalación normal de Orionis; no existe un extra ni configuración específica del módulo.
- La ejecución directa espera un event loop activo y la fachada de logging de Orionis iniciada.
- No se requiere un servicio externo salvo que lo necesite el callable envuelto.

## Inicio rápido

Asocia una tarea a una respuesta HTTP; Orionis la ejecuta después de enviar la respuesta:

```python
from orionis.background import BackgroundTask
from orionis.http.responses import Response


def record_delivery(message_id: int) -> None:
    print(f"delivered:{message_id}")


task = BackgroundTask(record_delivery, 42)
response = Response("accepted", status_code=202, background=task)

print(response.getStatusCode())       # 202
print(response.background is task)    # True
```

El fragmento construye la respuesta sin ejecutar la tarea. El adaptador ASGI/RSGI activo la llama después de completar el cuerpo.

Validación: **Executed successfully** en CPython 3.14.6.

## Conceptos principales

### Trabajo diferido de respuesta

Una respuesta posee como máximo un `BackgroundTask`. Como `BackgroundTasks` hereda de `BackgroundTask`, una colección puede ocupar ese lugar. “Background” significa después de entregar la respuesta, no un daemon separado: el adaptador espera su finalización antes de terminar el manejo de la respuesta.

### Clasificación de callables

Al construirse, `BackgroundTask` detecta funciones corrutina, objetos callable async y wrappers `functools.partial` de funciones async. Estos se ejecutan directamente en el loop actual. Los demás callables se ejecutan mediante `run_in_executor(None, ...)`; si uno devuelve un awaitable, la tarea espera después ese resultado en el loop.

### Colecciones ordenadas

`BackgroundTasks` conserva una lista pública mutable `tasks`. `addTask` envuelve el callable recibido y lo añade. La ejecución espera cada elemento en orden de inserción; la primera excepción detiene la colección y las tareas posteriores no se ejecutan.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `task.py` | Detección de callables, ejecución individual, despacho al ejecutor y logging. |
| `tasks.py` | Colección ordenada y método auxiliar `addTask`. |
| `contracts/task.py` | Contrato de extensión `IBackgroundTask` con `run()` async. |
| `__init__.py` | Reexporta `BackgroundTask` y `BackgroundTasks`. |

## API pública

### `BackgroundTask`

```text
BackgroundTask(func: Callable, *args: object, **kwargs: object)
```

El constructor guarda el callable y los argumentos, y clasifica el callable una sola vez. No valida que pueda llamarse ni ejecuta trabajo. Invoca una instancia mediante `await task()` o `await task.run()`; ambos devuelven `None`.

Si tiene éxito, registra un mensaje informativo con el nombre del callable. Si falla, registra un error y vuelve a lanzar la excepción original. Un objeto callable sin `__qualname__` se identifica por el nombre de su clase.

### `BackgroundTasks`

```text
BackgroundTasks(tasks: Sequence[BackgroundTask] | None = None)
```

El constructor copia la secuencia recibida en `tasks`; cambios posteriores en la secuencia de origen no afectan la colección. `None` y una secuencia vacía crean una colección vacía.

#### `addTask(func, *args, **kwargs)`

Envuelve el callable en `BackgroundTask`, lo añade y devuelve `None`. Se admite pasar otro objeto `BackgroundTasks` porque las colecciones también son objetos callable async, lo que permite grupos secuenciales anidados.

#### `run()` y `__call__()`

`__call__` espera las tareas almacenadas una a una. `run` se hereda de `BackgroundTask` y despacha dinámicamente al `__call__` de la colección. Ejecutar una colección vacía no hace nada.

### `IBackgroundTask`

El contrato de extensión solo exige `async run() -> None`. Las respuestas HTTP actualmente validan contra `BackgroundTask`, por lo que tareas personalizadas para respuestas normalmente deben heredar de `BackgroundTask` en lugar de limitarse a implementar el contrato.

## Flujos de trabajo comunes

### Ejecutar una acción después de una respuesta

Crea `BackgroundTask(callable, ...)` y pásala como argumento `background` de la respuesta. Devuelve desde el controlador; el transporte envía el cuerpo y después espera la tarea.

### Agrupar acciones relacionadas

Crea `BackgroundTasks`, llama `addTask` en el orden requerido y asocia la colección a la respuesta. Úsala cuando importe el orden; no ejecuta tareas concurrentemente.

### Ejecutar una tarea manualmente

Dentro de un contexto async de Orionis iniciado, usa `await task.run()` o `await task()`. La invocación manual sirve fuera de los adaptadores HTTP, pero sigue usando la fachada de logging y el loop actual.

## Ejemplos

### Construir una colección ordenada

```python
from orionis.background import BackgroundTasks
from orionis.http.responses import Response


def audit(event: str) -> None:
    print(event)


async def notify(address: str) -> None:
    print(f"notify:{address}")


tasks = BackgroundTasks()
tasks.addTask(audit, "account-created")
tasks.addTask(notify, "user@example.test")

response = Response({"created": True}, status_code=201, background=tasks)
print(len(tasks.tasks))  # 2
```

Cuando el transporte ejecuta la colección, `audit` termina antes de que comience `notify`.

Validación: **Executed successfully** en CPython 3.14.6; la invocación de tareas quedó cubierta por las pruebas del módulo porque requiere el logger iniciado.

### Ejecutar manualmente en un contexto async de Orionis

```python
from orionis.background import BackgroundTask


async def refresh_index(document_id: int) -> None:
    print(f"indexed:{document_id}")


async def after_import() -> None:
    await BackgroundTask(refresh_index, 17).run()
```

Llamar `after_import` imprime `indexed:17` y registra el éxito.

Validación: **Import-validated only** en CPython 3.14.6; la ejecución directa requiere la fachada de logging de Orionis iniciada.

### Conservar argumentos con nombre en trabajo síncrono

```python
from orionis.background import BackgroundTask


def export_report(*, report_id: int, format_name: str) -> None:
    print(f"{report_id}.{format_name}")


task = BackgroundTask(export_report, report_id=8, format_name="csv")
```

La implementación usa `functools.partial` para que los argumentos con nombre lleguen al callable ejecutado por `run_in_executor`.

Validación: **Executed successfully** en CPython 3.14.6; la construcción no necesita estado de aplicación.

### Manejar un fallo en el límite de ejecución

```python
from orionis.background import BackgroundTask


def fail_delivery() -> None:
    raise RuntimeError("delivery unavailable")


async def run_delivery() -> None:
    try:
        await BackgroundTask(fail_delivery).run()
    except RuntimeError as error:
        print(str(error))
```

La tarea registra el fallo y deja disponible el `RuntimeError` original para quien llama. En una colección, las tareas posteriores se omiten.

Validación: **Import-validated only** en CPython 3.14.6; la ejecución requiere la fachada de logging de Orionis iniciada.

## Configuración

El módulo no consume claves de configuración ni variables de entorno de Orionis. El tamaño del ejecutor pertenece al loop asyncio activo. El comportamiento de logging procede de la configuración normal de Orionis, no de este paquete.

## Integración con Orionis

`orionis.http.responses.Response` acepta un `BackgroundTask` en su argumento `background`. Los adaptadores ASGI y RSGI esperan `runBackground()` después de entregar cuerpos en memoria, streams ordinarios, archivos, respuestas vacías y framing HEAD. Los controladores de registro y restablecimiento de contraseña de Orionis usan este mecanismo para enviar correo fuera de la ruta crítica de la respuesta.

El módulo usa la fachada `Log` para registros de éxito y fallo. No tiene provider ni binding propio en el contenedor.

## Errores y casos límite

- La construcción no rechaza un objeto no callable; al invocarlo sigue la ruta síncrona, registra el `TypeError` resultante y lo vuelve a lanzar.
- Las excepciones nunca se ocultan. Un elemento fallido impide ejecutar todos los posteriores de la colección.
- `asyncio.CancelledError` es `BaseException`, no `Exception`, por lo que el manejador de logging no lo intercepta.
- El estilo del callable se clasifica una vez al construir. Reemplazar internals no está soportado.
- Fallos de entrega de la respuesta o ciertas rutas de desconexión de streams pueden impedir el trabajo de fondo. Usa `orionis.queues` para trabajo durable o con reintentos.
- Se admite una función síncrona que devuelve un awaitable: la función se ejecuta en el ejecutor y el awaitable continúa después en el event loop.

## Rendimiento y concurrencia

Las funciones síncronas se ejecutan en el ejecutor predeterminado del event loop y no ocupan su hilo mientras trabajan. Su límite de concurrencia y ciclo de cierre pertenecen al loop. Las funciones async se ejecutan normalmente y deben ceder control para permitir concurrencia.

`BackgroundTasks` es estrictamente secuencial y no crea un task group. Su lista pública no está protegida contra mutación concurrente; completa la colección antes de entregar la respuesta. El adaptador espera el trabajo de fondo, por lo que tareas largas aún consumen capacidad del worker aunque el cliente ya haya recibido la respuesta.

## Compatibilidad

El proyecto declara Python 3.14+; la validación usó CPython 3.14.6 en Windows. La implementación usa APIs estándar de `asyncio`, `inspect` y `functools`, y es independiente de la plataforma. Funciona mediante los adaptadores de respuesta ASGI y RSGI de Orionis.

## Notas de verificación

Se inspeccionaron la implementación, contrato, respuestas/adaptadores HTTP, consumidores directos en controladores y `tests/background`. Las 77 pruebas del módulo pasaron mediante el ejecutor Orionis en CPython 3.14.6. Se ejecutaron los ejemplos de construcción/respuesta; los que invocan tareas se validaron por import y su comportamiento de ejecución fue verificado por las pruebas porque el logging requiere una aplicación iniciada.
