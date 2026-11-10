# Gestionar excepciones

## Puntos de entrada de la aplicación

Registra una subclase de aplicación mediante `app.withExceptionHandler(ExceptionHandler)` antes de `create()`. Ambos métodos retornan el resultado heredado para que el runtime reciba el plan seleccionado:

```python
from orionis.failure.base import BaseExceptionHandler
from orionis.failure.entities import FailureContext, FailureHandling


class ExceptionHandler(BaseExceptionHandler):
    async def handleFailure(
        self, exception: BaseException, context: FailureContext,
    ) -> FailureHandling | None:
        return await super().handleFailure(exception, context)

    async def handleResult(
        self, value: object, context: FailureContext,
    ) -> FailureHandling | None:
        return await super().handleResult(value, context)
```

`IBaseExceptionHandler` declara exactamente estos dos hooks abstractos. Extender `BaseExceptionHandler` aporta ambas implementaciones predeterminadas. Implementar directamente el contrato exige ambos métodos. La aplicación prepara y reutiliza un handler fuera del scope de solicitudes; sus dependencias de constructor deben ser compatibles con esa duración.

Retornar `None` selecciona una recepción sin efectos diferidos. Esperar `super().handleFailure(...)` y descartar su retorno pierde el logging y la presentación predeterminados. No vuelvas a capturar desde un hook ni guardes estado de cada incidente en el handler compartido.

## Un incidente, un plan diferido

1. Un límite de ejecución entrega la excepción original y su `FailureContext` inmutable al runtime.
2. El runtime deduplica la propagación dentro de la operación e invoca `handleFailure` una vez para ese incidente.
3. `BaseExceptionHandler` construye un plan `FailureHandling` sin registrar ni renderizar. El runtime llama a su `complete()` bajo las protecciones de recursión, timeout y fallback.
4. Cuando un propietario HTTP o CLI necesita salida, `Catch.exception()` usa `present(flow=..., request=...)` del mismo plan. No vuelve a invocar un hook de aplicación. Los demás propietarios conservan su recuperación, respuesta de protocolo o propagación.

El plan pertenece al incidente, no al handler compartido. `complete()` ejecuta una vez su callback asíncrono opcional `logging()`. `present()` ejecuta una vez su callback asíncrono opcional `presentation(*, flow, request=None)` y conserva el resultado. Si un callback falla, se conserva ese fallo y las llamadas repetidas no lo reintentan. No ejecutes estos métodos dentro del hook de aplicación.

El logging predeterminado resuelve `ILogger` y escribe un registro de excepción usando `Throwable` y el traceback original. `context.expected=True` omite ese logging. Las clases exactas en `dont_catch` omiten logging y presentación, aunque el hook recibe la excepción original. Durante el cierre final, `context.reporting_allowed=False` también impide que el plan base programe logging; la política personalizada debe respetar ese indicador.

`handleResult` recibe un resultado declarado fallido sin construir una excepción ni un traceback. Su implementación base retorna `None`. Una implementación personalizada puede retornar un plan para logging diferido; capturar ese resultado no reemplaza el valor original ni presenta automáticamente una respuesta HTTP/CLI.

## Personalizar una respuesta HTTP

Este handler de aplicación convierte un conflicto de dominio en HTTP 409 y conserva el logging y la salida CLI heredados. Usa variables locales para que los incidentes concurrentes no se sobrescriban. Conserva el callback de presentación heredado antes de reemplazarlo; llamar a `present()` del propio plan dentro de ese callback produciría recursión.

```python
from orionis.failure.base import BaseExceptionHandler
from orionis.failure.entities import FailureContext, FailureHandling
from orionis.http import JSONResponse


class OrderConflict(Exception):
    pass


class ExceptionHandler(BaseExceptionHandler):
    async def handleFailure(
        self, exception: BaseException, context: FailureContext,
    ) -> FailureHandling | None:
        plan = await super().handleFailure(exception, context)
        if (
            not isinstance(exception, OrderConflict)
            or self.isExceptionIgnored(exception)
        ):
            return plan

        inherited_presentation = plan.presentation

        async def present(*, flow: str, request: object | None = None) -> object:
            if flow == "http":
                return JSONResponse(
                    {"message": "Order already processed"}, status_code=409,
                )
            if inherited_presentation is not None:
                return await inherited_presentation(flow=flow, request=request)
            return None

        plan.presentation = present
        return plan
```

Registra esta clase antes del inicio. No añadas `OrderConflict` a `dont_catch` si necesitas la respuesta 409, porque esa política también suprime la presentación. Para omitir solo logging de una excepción de negocio seleccionada, asigna `None` a `logging` del plan retornado. Para reemplazar logging, suministra un callback async que respete `context.reporting_allowed`; deja la ejecución al runtime.

## Política HTTP y CLI predeterminada

`Catch.exception()` lee `kernel` del scope activo. `KernelContext.CONSOLE` solicita `flow="cli"` y el plan base llama a `Console.exception`. `KernelContext.HTTP` solicita `flow="http"` con el request o adaptador. Otros valores de kernel no solicitan presentación. La ausencia de scope o `kernel` produce `RuntimeError`.

Las excepciones HTTP conocidas, incluidas sus subclases, se mapean a pares estables de estado y mensaje público. Los errores desconocidos muestran detalle solo con `app.debug` activo; producción retorna `500 Internal Server Error` genérico. JSON o HTML depende de `request.wantsJson()`. Los fallos de autenticación también reciben `WWW-Authenticate: Bearer` cuando el guard actual es `token`.

Dentro de un límite HTTP existente de una aplicación iniciada, usa la fachada cuando ese límite sea dueño de la respuesta:

```python
from orionis.support.facades import Catch


async def handle_failure(exception: BaseException, request):
    return await Catch.exception(exception, request)
```

Un fallo del logging no impide por sí solo la presentación. El runtime contiene los fallos del hook y del logging, y escribe diagnósticos de emergencia acotados en stderr con identidad de incidente y tipos de excepción. Evita mensajes sensibles y el stdout del protocolo. La cancelación y las excepciones de control de proceso conservan su comportamiento.

## Captura despues del inicio

HTTP y CLI activan la recepción después del inicio exitoso; HTTP sin lifespan la activa después de inicializar su kernel de forma diferida. `create()` por sí solo no activa esta garantía. Para ejecución headless, completa `await app.boot()` y delimita una ejecución propia:

```python
from orionis.failure.runtime import capture, operation

await app.boot()
try:
    with operation(app, flow="worker", operation="import", isolated=True):
        try:
            await service.run()
        except Exception as error:
            await capture(error, phase="execution")
            raise
finally:
    await app.aclose()
```

`operation()` establece contexto y deduplicación; no captura errores automáticamente. Su propietario notifica y conserva propagación, respuesta o recuperación. Incluye el consumo de streams dentro del límite. Las tareas creadas allí con `Loop.createTask` quedan supervisadas; las llamadas externas arbitrarias a `asyncio.create_task` necesitan su propio propietario explícito.

`aclose()` libera el propietario headless, cancela y drena las tareas supervisadas cuando finaliza el último propietario, y después cierra el logging. No ejecuta callbacks del lifecycle HTTP. La recepción sigue disponible durante la limpieza, con logging deshabilitado cuando se cierran sus recursos.

El servicio inyectado también admite `await catch.capture(error, context=FailureContext(flow="worker", phase="execution"))`. `FailureReceipt` distingue entrega, reporte, duplicado y degradación; `None` indica que no hay runtime activo o que se trata de una excepción de control excluida. La propagación repetida dentro de una operación comparte el incidente; los intentos y las operaciones independientes permanecen separados.

El contexto contiene origen, fase, correlación, `expected`, `reporting_allowed` y metadatos escalares acotados. No contiene request, socket ni scope. Mantén el request vivo en el propietario de la ejecución y pásalo solamente al solicitar presentación. No hay hooks globales de Python que observen código externo arbitrario; los fallos anteriores al inicio quedan fuera de la garantía del runtime.

## Fuentes y siguientes pasos

[Catch](../../catch.py) · [Handler base](../../base/handler.py) · [Plan de manejo](../../entities/handling.py) · [Runtime](../../runtime.py)

[Volver al índice del módulo](README.md).
