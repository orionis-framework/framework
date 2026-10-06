# orionis.failure

> `orionis.failure` centraliza el reporte de excepciones y renderiza fallos CLI o HTTP según el contexto Orionis.

## Descripción general

`Catch` es el servicio exportado por el paquete: recibe una excepción, resuelve perezosamente el handler de aplicación, reporta y despacha el renderizado según el kernel del scope activo. Console usa `handleCLI`; HTTP usa `handleHTTP`; contextos desconocidos solo reportan.

`BaseExceptionHandler` aporta la política predeterminada: conversión a `Throwable`, logging, render CLI, mapeo de estados HTTP, respuestas 500 saneadas en producción y detalle en debug. La aplicación puede registrar otro handler que satisfaga `IBaseExceptionHandler`.

## Requisitos

- Python 3.14 o posterior.
- Aplicación/contenedor Orionis iniciado para `Catch.exception()` o la fachada `Catch`.
- Scope activo con contexto `kernel`.
- Request o adaptador de transporte al manejar una excepción HTTP.
- Servicios de logging, consola y respuestas resolubles para el método elegido.

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

Validación: **Executed successfully** en CPython 3.14.6; se ejercitó solo la conversión sin dependencias.

## Conceptos principales

### Reportar antes de renderizar

`Catch.exception()` invoca `report` después de resolver kernel y luego el renderer correspondiente. `call()` del contenedor inyecta parámetros como `ILogger` y `Console` a los métodos predeterminados.

### Despacho por contexto

`KernelContext.CONSOLE` renderiza en consola y retorna `None`. `KernelContext.HTTP` retorna `Response` o `None`. Otro valor reporta pero no renderiza. La ausencia de scope o `kernel` es error de configuración runtime.

### Política HTTP pública

Excepciones conocidas mapean a pares estables de estado/mensaje. Errores desconocidos muestran detalle solo con `app.debug`; producción retorna `500 Internal Server Error`. La negociación viene de `request.wantsJson()`.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `catch.py` | Resolución del handler, reporte y despacho por kernel. |
| `base/handler.py` | Reporte, salida CLI, mapeo HTTP y política debug. |
| `entities/throwable.py` | Registro estructurado congelado y slotted. |
| `enums/kernel_type.py` | Marcadores `CONSOLE` y `HTTP`. |
| `contracts/` | Interfaces abstractas de catch y handler. |
| `provider.py` | Binding singleton y fijación de fachada. |

## API pública

### `Catch(app)`

Único símbolo exportado por `orionis.failure`. Su método async `exception(exception, request=None)` resuelve/cachea handler, lee `kernel`, reporta y despacha. Construcción directa es principalmente infraestructura; aplicaciones usan la fachada o reciben `ICatch` por inyección.

### `BaseExceptionHandler`

- `toThrowable(exception)` convierte argumentos a string y conserva traceback nativo.
- `isExceptionIgnored(exception)` prueba membresía exacta en `dont_catch`.
- `report(exception, log)` registra `[ClassName] message` y retorna `Throwable`, o `None` si se ignora.
- `handleCLI(exception, console)` delega a `console.exception` salvo ignorados.
- `handleHTTP(exception, request)` construye respuesta mapeada, de producción o debug.

### `Throwable`

Dataclass congelada, keyword-only y slotted con `classtype`, `message`, `args` como strings y `traceback` nativo opcional. No se serializa ni formatea por sí sola.

### Contratos y fachada

`ICatch` se exporta desde `orionis.failure.contracts`; `IBaseExceptionHandler` está en su módulo definidor. La fachada es `orionis.support.facades.Catch`, distinta del export concreto.

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

Validación: **Executed successfully** en CPython 3.14.6; se restauró el estado compartido de clase.

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

Validación: **Executed successfully** en CPython 3.14.6.

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

Validación: **Executed successfully** en CPython 3.14.6 con doble de aplicación aislado.

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

Validación: **Executed successfully** en CPython 3.14.6; produjo `404 Route not found`.

### Usar la fachada en aplicación iniciada

```python
from orionis.support.facades import Catch

response = await Catch.exception(exception, request)
```

Validación: **Import-only** en CPython 3.14.6; las variables ilustrativas y el scope provienen del kernel activo.

## Configuración

No existe config dedicada. El handler lee `app.debug`:

| Valor | Excepción HTTP desconocida |
|---|---|
| `False` | Estado 500 saneado con `Internal Server Error`. |
| `True` | Respuesta detallada con path/método y excepción. |

La clase handler se registra mediante la API de aplicación. `dont_catch` es política en código, no ajuste de entorno.

## Integración con Orionis

`CatchProvider` es core. Vincula `ICatch` al singleton `Catch` con alias `x-orionis-ICatch` y fija la fachada. Kernel HTTP, reactor console, scheduler y middleware de session inyectan `ICatch` para llevar fallos a una sola política.

La aplicación resuelve su handler configurado, predeterminado `BaseExceptionHandler`. Las llamadas del contenedor inyectan logging, console y responses. Fallos de autenticación token reciben además `WWW-Authenticate: Bearer` si el guard actual es `token`.

## Errores y casos límite

- Scope activo o `kernel` ausente lanza `RuntimeError`; no se puede reportar con seguridad.
- Contexto HTTP sin request usable falla al pedir `wantsJson()`; pasa siempre request/adaptador.
- `isExceptionIgnored` exige instancia `BaseException` y rechaza otros objetos con `TypeError`.
- Ignorar compara exactamente `type(exception)`; el mapeo HTTP recorre MRO e incluye subclases.
- Si el reporte falla, no se ejecuta el renderer.
- `KeyboardInterrupt`, `SystemExit` y otros `BaseException` pueden llegar; decídelo explícitamente.

Estados mapeados: 401 autenticación, 403 autorización, 404 ruta, 405 método, 413 payload, 415 media type y 419 CSRF.

## Rendimiento y concurrencia

La primera llamada concurrente resuelve el handler detrás de `asyncio.Lock`; las siguientes lo reutilizan sin lock. Scope y kernel se consultan por excepción porque son locales al contexto. Conversión y mapeo son operaciones pequeñas; logging y render dominan el costo.

El singleton conserva solo el handler resuelto; request y excepción son locales a cada corrutina. Handlers personalizados deben mantener esa propiedad para concurrencia HTTP segura.

## Compatibilidad

Orionis declara Python 3.14+. El módulo depende de contratos Orionis HTTP, auth, logging, console y container, sin dependencia externa separada. La validación usó CPython 3.14.6 en Windows.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, contratos, dispatcher, handler base, mapeos HTTP, entidad, enum, provider, fachada, kernels y `tests/failure`. Las 91 pruebas pasaron con el runner Orionis. Cinco programas directos se ejecutaron correctamente; el snippet de fachada solo se validó por importación.
