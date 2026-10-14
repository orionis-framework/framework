# Reportar y gestionar excepciones

## Inicio rápido

```python
from orionis.failure.base import BaseExceptionHandler

handler = BaseExceptionHandler(object(), object())
error = ValueError("invalid value", 7)
throwable = handler.toThrowable(error)

assert throwable.classtype is ValueError
assert throwable.message == "invalid value"
assert throwable.args == ("invalid value", "7")
print(throwable.classtype.__name__, throwable.message)
```

## Conceptos principales

### Reportar antes de renderizar

`Catch.exception()` invoca `report` después de resolver kernel y luego el renderer correspondiente. `call()` del contenedor inyecta parámetros como `ILogger` y `Console` a los métodos predeterminados.

### Despacho por contexto

`KernelContext.CONSOLE` renderiza en consola y retorna `None`. `KernelContext.HTTP` retorna `Response` o `None`. Otro valor reporta pero no renderiza. La ausencia de scope o `kernel` es error de configuración runtime.

### Política HTTP pública

Excepciones conocidas mapean a pares estables de estado/mensaje. Errores desconocidos muestran detalle solo con `app.debug`; producción retorna `500 Internal Server Error`. La negociación viene de `request.wantsJson()`.

## Flujos de trabajo comunes

### Personalizar excepciones ignoradas

Define `dont_catch` de una subclase como `frozenset` de clases exactas. Las coincidentes omiten log y render. Subclases no se ignoran implícitamente, evitando silenciar familias más amplias.

### Instalar un handler personalizado

Subclasifica o implementa `IBaseExceptionHandler`, conserva firmas inyectables y regístralo mediante la API de handler de aplicación. `Catch` lo resuelve una vez y reutiliza.

### Retornar fallos API seguros

Lanza excepciones framework de autenticación, autorización, routing, payload, media type o CSRF. El handler las mapea sin importar debug y solicita a `DefaultResponses` JSON o HTML según request.

## Ejemplos

### Ignorar una clase exacta

```python
from orionis.failure.base import BaseExceptionHandler


class QuietError(Exception):
    pass


class ChildError(QuietError):
    pass


handler = BaseExceptionHandler(object(), object())
BaseExceptionHandler.dont_catch = frozenset({QuietError})
assert handler.isExceptionIgnored(QuietError("quiet"))
assert not handler.isExceptionIgnored(ChildError("child"))
BaseExceptionHandler.dont_catch = frozenset()
print("exact matching ok")
```


### Reportar mediante logger

```python
import asyncio
from orionis.failure.base import BaseExceptionHandler


class Log:
    def __init__(self) -> None:
        self.messages = []

    def error(self, message: str) -> None:
        self.messages.append(message)


handler = BaseExceptionHandler(object(), object())
log = Log()
result = asyncio.run(handler.report(RuntimeError("boom"), log))
assert result is not None
assert log.messages == ["[RuntimeError] boom"]
print(log.messages[0])
```


### Despachar un fallo de consola

```python
import asyncio
from orionis.failure import Catch
from orionis.failure.enums import KernelContext


class Scope:
    async def get(self, name: str):
        assert name == "kernel"
        return KernelContext.CONSOLE


class Handler:
    def __init__(self) -> None:
        self.calls = []

    async def report(self, exception: BaseException) -> None:
        self.calls.append(("report", str(exception)))

    async def handleCLI(self, exception: BaseException) -> None:
        self.calls.append(("cli", str(exception)))


class App:
    def __init__(self) -> None:
        self.handler = Handler()

    async def getExceptionHandler(self):
        return self.handler

    def getCurrentScope(self):
        return Scope()

    async def call(self, target, method: str, **kwargs):
        return await getattr(target, method)(**kwargs)


app = App()
assert asyncio.run(Catch(app).exception(RuntimeError("boom"))) is None
assert app.handler.calls == [("report", "boom"), ("cli", "boom")]
print(app.handler.calls)
```


### Mapear fallo de ruta a HTTP 404

```python
import asyncio
from orionis.failure.base import BaseExceptionHandler
from orionis.http.routes.exceptions.route_not_found import RouteNotFound


class Responses:
    async def error(self, **kwargs):
        return kwargs

    async def exception(self, **kwargs):
        return kwargs


class App:
    def config(self, name: str):
        assert name == "app.debug"
        return False


class Request:
    path = "/missing"
    method = "GET"

    def wantsJson(self) -> bool:
        return True


handler = BaseExceptionHandler(Responses(), App())
response = asyncio.run(handler.handleHTTP(RouteNotFound("missing"), Request()))
assert response == {
    "status_code": 404,
    "content": "Route not found",
    "expects_json": True,
}
print(response["status_code"], response["content"])
```


### Usar la fachada en aplicación iniciada

```python
from orionis.support.facades import Catch

async def handle_failure(exception: BaseException, request):
    return await Catch.exception(exception, request)
```

## Integración con Orionis

`CatchProvider` es core. Vincula `ICatch` al singleton `Catch` con alias `x-orionis-ICatch` y fija la fachada. Kernel HTTP, reactor console, scheduler y middleware de session inyectan `ICatch` para llevar fallos a una sola política.

La aplicación resuelve su handler configurado, predeterminado `BaseExceptionHandler`. Las llamadas del contenedor inyectan logging, console y responses. Fallos de autenticación token reciben además `WWW-Authenticate: Bearer` si el guard actual es `token`.

## Convertir un conflicto de dominio en una respuesta

En una aplicación, guarda este módulo en `app/exceptions/handler.py` y registra `ExceptionHandler` mediante `app.withExceptionHandler(ExceptionHandler)` antes de `create()`. El handler conserva la política nativa para el resto de errores. El estado de cada error queda en variables locales, no en atributos del singleton.

`Catch` llama a `report` antes de renderizar. Por tanto, este conflicto todavía se registra mediante la política heredada. No añadas `OrderConflict` a `dont_catch` si necesitas devolver la respuesta 409: esa colección suprime también el renderizado. Cuando ajustes la política de logging, sobrescribe `report` de forma explícita y conserva las dependencias inyectadas que necesites. Un fallo del logger interrumpe el flujo antes del renderer.

```python
from orionis.failure.base import BaseExceptionHandler
from orionis.http import JSONResponse, Response, Request
from orionis.http.adapters.request.contracts.transport import TransportAdapter

class OrderConflict(Exception):
    pass

class ExceptionHandler(BaseExceptionHandler):
    async def handleHTTP(
        self,
        exception: BaseException,
        request: Request | TransportAdapter,
    ) -> Response | None:
        if isinstance(exception, OrderConflict):
            return JSONResponse({"message": "Order already processed"}, status_code=409)
        return await super().handleHTTP(exception, request)
```

## Fuentes y siguientes pasos

[catch.py](../../catch.py) · [handler.py](../../base/handler.py) · [provider.py](../../provider.py)

[Volver al índice del módulo](README.md).
