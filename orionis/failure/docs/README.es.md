# orionis.failure

> Reportar excepciones y delegar su presentación al manejador CLI o HTTP.

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

`Catch` conecta las excepciones con el manejador configurado en la aplicación.
Lee el kernel del scope actual del contenedor, reporta la excepción y después
delega su presentación CLI o HTTP. `BaseExceptionHandler` proporciona registro,
salida de traceback en consola y respuestas HTTP de error; `Throwable` conserva
los detalles nativos de la excepción sin serializarlos.

### Inventario de fuentes

Todas las rutas siguientes son relativas a `orionis/failure/`. Son los 12 archivos
Python del módulo; ninguno de los inicializadores está vacío.

| Archivo | API definida o comportamiento del paquete |
|---|---|
| `__init__.py` | Exporta `Catch` de forma diferida; `__getattr__`, `__dir__`. |
| `catch.py` | `Catch.__init__`, `Catch.exception` asíncrono. |
| `base/__init__.py` | Exporta `BaseExceptionHandler`. |
| `base/handler.py` | `BaseExceptionHandler.__init__`, `toThrowable`, `isExceptionIgnored`, `report`, `handleCLI`, `handleHTTP` asíncronos; `_HTTP_STATUS_MAP` privado. |
| `contracts/__init__.py` | Exporta `ICatch`, no `IBaseExceptionHandler`. |
| `contracts/catch.py` | `ICatch` y `exception` abstracto asíncrono. |
| `contracts/handler.py` | `IBaseExceptionHandler` y sus cinco métodos abstractos. |
| `entities/__init__.py` | Exporta `Throwable`. |
| `entities/throwable.py` | Dataclass `Throwable` congelada, con parámetros por nombre y slots. |
| `enums/__init__.py` | Exporta `KernelContext`. |
| `enums/kernel_type.py` | `KernelContext(Enum)` con `CONSOLE` y `HTTP`. |
| `provider.py` | `CatchProvider.register`, `CatchProvider.boot` asíncrono. |

No hay funciones públicas ordinarias a nivel de módulo ni métodos auxiliares
privados. Los constructores y hooks del paquete son los únicos métodos especiales
explícitos. Las operaciones de dataclass y Enum se generan o heredan; no son API
escrita manualmente.

### Integración y orden de ejecución

Las dependencias internas directas son `orionis.foundation` (`IApplication`),
`orionis.container` (`ServiceProvider`), `orionis.http` (`Request`,
`TransportAdapter`, `Response`, `DefaultResponses` y excepciones mapeadas),
`orionis.console` (`Console`), `orionis.logging` (`ILogger`), `orionis.auth`
(excepciones y `current_auth_context`), `orionis.support.facades.catch`
(la fachada independiente) y `orionis._exports` (exportación diferida del paquete).

`Catch.exception` ejecuta estos pasos en orden:

1. Resuelve y guarda `app.getExceptionHandler()` si no hay un manejador en caché.
2. Exige `app.getCurrentScope()` y espera `scope.get("kernel")`.
3. Espera `app.call(handler, "report", exception=exception)`.
4. Para `KernelContext.CONSOLE`, devuelve el resultado de `handleCLI` mediante `app.call`.
5. Para `KernelContext.HTTP`, devuelve el resultado de `handleHTTP`, pasando `request`.
6. Para cualquier otro contexto distinto de `None`, devuelve `None` tras reportar.

Las comparaciones del enum usan identidad (`is`), no igualdad de strings o enteros.
El retorno de `report` no controla el despacho: devolver `None` desde `report`
no impide llamar a `handleCLI` o `handleHTTP`.

### Decisiones de diseño

- Separación de contrato e implementación: `ICatch` e `IBaseExceptionHandler` exponen responsabilidades distintas de despacho y presentación.
- Singleton administrado por el contenedor: `CatchProvider` comparte una instancia de `Catch`, incluido su manejador en caché, entre llamadas.
- Resolución diferida del manejador: la primera excepción lo resuelve incluso antes de comprobar el scope.
- Dataclass congelada y con slots: `Throwable` impide reasignar campos pero conserva la referencia al traceback mutable original.
- Conjunto de exclusión por tipo exacto: ignorar una excepción base no ignora implícitamente sus subclases.
- Mapeo HTTP por MRO: las subclases heredan el estado y mensaje público del primer ancestro mapeado.
- Sin `__slots__` declarados en manejadores, despachador o contratos: a diferencia de `Throwable`, estas instancias tienen un diccionario de instancia.

## Referencia de API

Las firmas en bloques `text` reproducen las declaraciones del código, incluidos
`self`, anotaciones y valores predeterminados. Son fragmentos de referencia,
no ejemplos ejecutables. Los bloques `python` de Ejemplos de uso son scripts
completos e independientes.

> ⚠️ No especificado en el código fuente: `Catch`, `BaseExceptionHandler`, `ICatch`, `IBaseExceptionHandler` y `CatchProvider` no tienen docstring propio de clase. El comportamiento siguiente se establece a partir de cuerpos de métodos, sus docstrings y declaraciones, no de una descripción de clase heredada.

### Catch

Import: `from orionis.failure import Catch` o
`from orionis.failure.catch import Catch`. Es el servicio, no la fachada.
Hereda de `ICatch`.

```text
	def __init__(self, app: IApplication) -> None:

	async def exception(
		self,
		exception: BaseException,
		request: Request | TransportAdapter | None = None,
	) -> Response | None:
```

- `app: IApplication`: proporciona resolución del manejador, scope actual y `call` con inyección de dependencias. El constructor lo guarda, inicializa la caché del manejador a `None` y crea un `asyncio.Lock`; devuelve `None`.
- `exception: BaseException`: se pasa sin cambios a `report` y al método de presentación seleccionado.
- `request: Request | TransportAdapter | None = None`: solo se pasa al manejo HTTP. El valor predeterminado sirve para consola; el manejador HTTP base exige un objeto distinto de `None` con `wantsJson()`.
- Retorno: `Response | None`; el manejador CLI base devuelve `None`, el HTTP base una respuesta o `None` si se ignora. Los resultados de manejadores personalizados se devuelven sin validar su tipo en ejecución.
- Lanza `RuntimeError` cuando el scope es `None` (`No active scope found for context retrieval.`) o su kernel es `None` (`No kernel found in the current scope for context retrieval.`).
- Se propagan los fallos de resolución, consulta del scope y todas las llamadas `app.call`. Un fallo en `report` impide presentar el error; no hay respaldo ni reintento alrededor de estas llamadas.
- Efectos: conserva un manejador resuelto correctamente; registra y presenta mediante servicios inyectados. Aquí no se crea automáticamente un scope, se relanza la excepción, se termina el proceso ni se transmite la respuesta.

La implementación concreta `Application.getExceptionHandler()` exige una
aplicación arrancada, guarda en caché la **clase** del manejador y usa `build()`
para crear una instancia en cada llamada. `Catch` conserva por separado la primera
instancia que obtiene. Si la resolución falla, su caché queda vacía y una llamada
posterior puede intentar resolver de nuevo.

### BaseExceptionHandler

Import: `from orionis.failure.base import BaseExceptionHandler` o
`from orionis.failure.base.handler import BaseExceptionHandler`.
Hereda de `IBaseExceptionHandler`.

```text
	dont_catch: ClassVar[frozenset[type[BaseException]]] = frozenset()

	def __init__(
		self,
		default_responses: DefaultResponses,
		application: IApplication,
	) -> None:

	def toThrowable(
		self,
		exception: BaseException,
	) -> Throwable:

	def isExceptionIgnored(
		self,
		exception: BaseException,
	) -> bool:

	async def report(
		self,
		exception: BaseException,
		log: ILogger,
	) -> Throwable | None:

	async def handleCLI(
		self,
		exception: BaseException,
		console: Console,
	) -> None:

	async def handleHTTP(
		self,
		exception: BaseException,
		request: Request | TransportAdapter,
	) -> Response | None:
```

**Constructor.** `default_responses: DefaultResponses` presenta errores HTTP y
páginas debug; `application: IApplication` proporciona `config("app.debug")`.
Guarda ambas dependencias, devuelve `None` y no presenta ni registra nada.

**toThrowable.** Convierte `exception: BaseException` en un `Throwable`.
Usa `exception.args or ("",)`, aplica `str` a cada argumento y toma el primer
string como `message`. No equivale necesariamente a `str(exception)`; por ejemplo,
no usa las comillas de `KeyError` ni el `__str__` de una excepción personalizada
para construirlo. Conserva `type(exception)` y la referencia original a
`exception.__traceback__`. No muta, registra ni valida explícitamente la entrada;
se propagan los fallos al leer atributos o convertir argumentos a strings.

**isExceptionIgnored.** `exception: BaseException` debe ser una instancia de
excepción; de lo contrario lanza `TypeError` con
`Expected BaseException, got <type name>`. Devuelve como `bool`
`type(exception) in self.dont_catch`. No tiene efectos secundarios.
El `frozenset` vacío predeterminado no ignora nada. Reemplazar el atributo de
clase afecta a las instancias que lo usan; una subclase puede declarar el suyo.

**report.** Comprueba `exception: BaseException` contra `dont_catch`.
`log: ILogger` recibe una llamada síncrona `log.error` con el formato
`[<exception class name>] <first stringified argument>`. Devuelve el `Throwable`
convertido, o `None` sin registrar si se ignora. Este método no pasa el traceback,
los argumentos restantes ni la cadena de excepciones a `log.error`.
Se propagan el `TypeError` de la comprobación y los fallos de conversión o logger.
La corrutina no contiene `await`; el logger proporcionado puede realizar E/S
síncrona. En llamadas directas hay que proporcionar `log`; `Catch` lo aporta por DI.

**handleCLI.** Comprueba `exception: BaseException` contra `dont_catch`.
`console: Console` recibe `console.exception(exception)` salvo que se ignore.
Devuelve `None` en ambos casos; no solicita código de salida ni terminar el proceso.
Se propagan el `TypeError` de la comprobación y los fallos de consola. No hay
`await` dentro de esta corrutina. En llamadas directas hay que proporcionar
`console`; `Catch` usa DI.

**handleHTTP.** Comprueba `exception: BaseException` contra `dont_catch` antes
de acceder a `request: Request | TransportAdapter`. Un error ignorado devuelve
`None`. En otro caso llama a `request.wantsJson()` y recorre
`type(exception).__mro__`:

| Primer ancestro mapeado | Estado HTTP | Contenido público exacto |
|---|---|---|
| `AuthenticationException` | 401 | `Unauthenticated` |
| `AuthorizationException` | 403 | `This action is unauthorized` |
| `RouteNotFound` | 404 | `Route not found` |
| `MethodNotAllowed` | 405 | `Method not allowed` |
| `PayloadTooLargeException` | 413 | `Payload too large` |
| `UnsupportedMediaTypeException` | 415 | `Unsupported media type` |
| `CSRFTokenMismatchException` | 419 | `CSRF token mismatch` |

Los errores mapeados llaman a `await DefaultResponses.error` con el contenido
fijo y `expects_json=request.wantsJson()`, independientemente del modo debug.
Los errores de autenticación reciben además `WWW-Authenticate: Bearer` si
`current_auth_context().guard == "token"`. La decisión lee el contexto de
autenticación, no el header Authorization de la petición.

Un error no mapeado con `application.config("app.debug")` falsy usa estado 500,
contenido `Internal Server Error` y la misma preferencia JSON. `DefaultResponses`
produce un `JSONResponse` con `{"message": content}` o presenta HTML.

Un error no mapeado con configuración debug truthy llama a
`await DefaultResponses.exception(..., status_code=500)`, que devuelve un
`HTMLResponse` incluso si `wantsJson()` era true. Pasa la excepción original
y el path/método de la petición. Para un `TransportAdapter` real llama a `path()`
y `method()`; en otro caso lee `request.path` y `request.method` como propiedades.

No lee el estado desde `code` u otro atributo personalizado de la excepción.
Esta clase no contiene lógica de validación para 422 o redirecciones.
Una `ValidationException` sin manejo separado en la capa HTTP sigue aquí la ruta
de error no mapeado. Este manejador no añade `Allow` para `MethodNotAllowed`.

Lanza `TypeError` si la entrada no es una excepción. Una excepción HTTP no
ignorada con `request=None` lanza `AttributeError` al acceder a `wantsJson()`.
Los fallos de acceso a petición/configuración, consulta de autenticación,
renderizado de plantillas, creación de respuesta y headers se propagan sin
captura dentro de este método. Presentar puede implicar E/S de plantillas;
se devuelve la respuesta, no se envía.

### ICatch

Import: `from orionis.failure.contracts import ICatch` o desde su módulo de
definición `orionis.failure.contracts.catch`. Hereda de `abc.ABC`.

```text
	@abstractmethod
	async def exception(
		self,
		exception: BaseException,
		request: Request | TransportAdapter | None = None,
	) -> Response | None:
```

Los parámetros y el tipo de retorno coinciden con `Catch.exception`. El método
abstracto solo contiene un docstring; no proporciona despacho ni excepciones
explícitas. No se puede instanciar `ICatch` hasta implementar `exception`
(`TypeError` del mecanismo ABC).

> ⚠️ No especificado en el código fuente: el contrato no impone reporte, comportamiento de scope ni excepciones de implementaciones de terceros.

### IBaseExceptionHandler

Importar directamente desde `orionis.failure.contracts.handler`; no se reexporta
en `orionis.failure.contracts`. Hereda de `abc.ABC`.

```text
	@abstractmethod
	def toThrowable(
		self,
		exception: BaseException,
	) -> Throwable:

	@abstractmethod
	def isExceptionIgnored(
		self,
		exception: BaseException,
	) -> bool:

	@abstractmethod
	async def report(
		self,
		exception: BaseException,
		log: ILogger,
	) -> Throwable | None:

	@abstractmethod
	async def handleCLI(
		self,
		exception: BaseException,
		console: IConsole,
	) -> None:

	@abstractmethod
	async def handleHTTP(
		self,
		exception: BaseException,
		request: Request | TransportAdapter,
	) -> Response | None:
```

`exception` es la excepción original; `log` el logger de reporte; `console`
la dependencia de salida CLI; `request` proporciona contexto HTTP.
`toThrowable` devuelve detalles estructurados, `isExceptionIgnored` una decisión
de exclusión, `report` detalles o `None`, `handleCLI` devuelve `None` y
`handleHTTP` una respuesta o `None`. Los cinco métodos son abstractos y solo
contienen docstring. Una implementación incompleta impide instanciar con
`TypeError`. El contrato anota `console` como `IConsole`; el concreto usa `Console`.

> ⚠️ No especificado en el código fuente: los cuerpos abstractos no prescriben efectos secundarios, mapeos HTTP ni excepciones de manejadores personalizados.

### Throwable

Import: `from orionis.failure.entities import Throwable` o
`from orionis.failure.entities.throwable import Throwable`.

Se muestra la declaración literal porque el constructor lo genera `dataclass`;
no está declarado con `def`:

```text
@dataclass(frozen=True, kw_only=True, slots=True)
class Throwable:
	classtype: type
	message: str
	args: tuple
	traceback: TracebackType | None = None
```

Construir con argumentos por nombre. `classtype: type`, `message: str` y
`args: tuple` son obligatorios; `traceback: TracebackType | None` vale `None`
por defecto. `BaseExceptionHandler.toThrowable` proporciona una tupla de strings,
pero la anotación real del campo es `tuple`, no `tuple[str, ...]`.

El constructor devuelve un `Throwable` nuevo; no hay validación personalizada ni
E/S. Python rechaza argumentos obligatorios ausentes o argumentos posicionales
con `TypeError`. Reasignar un campo declarado lanza
`dataclasses.FrozenInstanceError`. Los campos congelados no congelan profundamente
los objetos referenciados; guardar un traceback conserva acceso a sus frames.
La entidad no hereda de `BaseEntity`, no expone `toDict()`/`toJson()`, no formatea
tracebacks ni incluye campos explícitos de causa/contexto.

### KernelContext

Import: `from orionis.failure.enums import KernelContext` o
`from orionis.failure.enums.kernel_type import KernelContext`.

```text
class KernelContext(Enum):
	CONSOLE = auto()
	HTTP = auto()
```

Los dos miembros estándar de Enum tienen valores 1 y 2 respectivamente. No se
declaran métodos ni constructor personalizados. La búsqueda estándar de Enum
puede lanzar `ValueError` para un valor desconocido y `KeyError` para un nombre
inexistente. `Catch` exige los objetos miembro para despachar: `"HTTP"`, `"http"`
y `2` no son contextos HTTP para sus comprobaciones de identidad. Este módulo
no escribe la clave `"kernel"` del scope.

### CatchProvider

Import: `from orionis.failure.provider import CatchProvider`.
Hereda de `orionis.container.providers.service_provider.ServiceProvider` y está
registrado en `orionis.foundation.core_providers` como proveedor eager.

Declaración del constructor heredado de `ServiceProvider`:

```text
	def __init__(
		self,
		app: IApplication,
	) -> None:
```

Guarda `app: IApplication` como `self.app`; el constructor devuelve `None`.

```text
	def register(self) -> None:

	async def boot(self) -> None:
```

`register()` no recibe parámetros adicionales, devuelve `None` y llama a
`self.app.singleton(ICatch, Catch, alias="x-orionis-ICatch")`. No registra
`IBaseExceptionHandler` ni construye un manejador. Se propagan los fallos de registro.

`boot()` no recibe parámetros adicionales, devuelve `None` y espera
`CatchFacade.pin()`, mutando el estado compartido de la fachada fijada. Se
propagan los fallos de resolución o fijación. Registrar el proveedor no fija por
sí solo la fachada. Usar `await CatchFacade.exception(...)` al llamarla; la
operación subyacente sigue siendo asíncrona después de fijarla.

### Hooks del paquete

Definidos en `orionis.failure.__init__`:

```text
def __getattr__(name: str) -> object:

def __dir__() -> list[str]:
```

`__getattr__` recibe `name: str`, delega en `orionis._exports.resolve_export`
y devuelve el objeto exportado. Acceder a `Catch` importa su módulo bajo demanda
y guarda la exportación en el espacio de nombres del paquete. Los nombres
desconocidos lanzan `AttributeError`; los fallos de importación se propagan.
`__dir__` no recibe argumentos y devuelve como `list[str]` los nombres cargados
y las exportaciones declaradas ordenados, sin resolver las exportaciones.

## Ejemplos de uso

Cada bloque es un script Python 3.14+ independiente. El ejemplo HTTP usa un objeto
de configuración pequeño y plantillas en memoria: no necesita bootstrap de
aplicación ni servidor web. Estos dobles explícitos no son nuevas API del framework.

### Manejar un error HTTP

Construir los componentes reales `BaseExceptionHandler`, `DefaultResponses`,
`Directory` y `Jinja2Engine`; pasar un adaptador ASGI real e inspeccionar la
respuesta. Un error mapeado oculta el mensaje privado incluso en modo debug.

```python
import asyncio
import json
from pathlib import Path
from jinja2 import DictLoader, Environment
from orionis.failure.base import BaseExceptionHandler
from orionis.foundation.directory import Directory
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.default.responses import DefaultResponses
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.view.engine import Jinja2Engine

class Settings:
	def config(self, key: str) -> object:
		return {"app.name": "Example", "app.locale": "en",
				"app.debug": True}[key]

	def path(self) -> dict[str, Path]:
		return {"root": Path.cwd()}

class Templates:
	def getJinjaEnvironment(self) -> Environment:
		return Environment(loader=DictLoader({}), enable_async=True)

async def main() -> None:
	app = Settings()
	responses = DefaultResponses(app, Directory(app), Jinja2Engine(Templates()))
	handler = BaseExceptionHandler(responses, app)
	adapter = ASGITransportAdapter({
		"type": "http", "method": "GET", "path": "/missing",
		"scheme": "http", "server": ("localhost", 8000),
		"headers": [(b"accept", b"application/json")],
		"query_string": b"",
	})
	error = RouteNotFound("Private routing details")
	result = await handler.handleHTTP(error, adapter)
	assert result is not None
	assert json.loads(result.getBody()) == {"message": "Route not found"}
	print(result.getStatusCode(), result.getBody().decode())

asyncio.run(main())
```

### Conservar un traceback y manejar la inmutabilidad

Se puede construir `Throwable` sin DI. Capturar el error de reasignación no
descarta el traceback almacenado ni cambia su mensaje.

```python
from dataclasses import FrozenInstanceError
from orionis.failure.entities import Throwable

message = "Invalid input"
try:
	raise ValueError(message)
except ValueError as error:
	details = Throwable(
		classtype=type(error), message=str(error), args=error.args,
		traceback=error.__traceback__,
	)

assert details.traceback is not None
try:
	details.message = "Changed"
except FrozenInstanceError:
	print("Throwable fields are frozen")
assert details.message == message
```

### Despachar mediante un scope del contenedor

Usar el scope y la inyección mediante `call()` del `Container` real con un
manejador personalizado solo CLI. Su reporte y presentación sustituyen el
comportamiento base; escribe en salida estándar en lugar de configurar `ILogger`
o `Console`. Solo usa el `toThrowable` heredado, no el renderizador HTTP base.
En una aplicación real, seleccionar una clase de manejador importable con
`Application.withExceptionHandler()` antes de bloquear la configuración de arranque.

```python
import asyncio
from orionis.container.container import Container
from orionis.failure import Catch
from orionis.failure.base import BaseExceptionHandler
from orionis.failure.contracts.handler import IBaseExceptionHandler
from orionis.failure.entities import Throwable
from orionis.failure.enums import KernelContext

class CLIHandler(BaseExceptionHandler):
	def __init__(self) -> None:
		pass

	async def report(self, exception: BaseException) -> Throwable | None:
		details = self.toThrowable(exception)
		print("Reported:", details.classtype.__name__)
		return details

	async def handleCLI(self, exception: BaseException) -> None:
		print("CLI:", self.toThrowable(exception).message)

class ExampleContainer(Container):
	async def getExceptionHandler(self) -> IBaseExceptionHandler:
		return CLIHandler()

async def main() -> None:
	app = ExampleContainer()
	catch = Catch(app)
	message = "Example failure"
	async with app.beginScope() as scope:
		scope.set("kernel", KernelContext.CONSOLE)
		result = await catch.exception(ValueError(message))
		assert result is None
	try:
		await catch.exception(ValueError(message))
	except RuntimeError as error:
		print(error)

asyncio.run(main())
```

La última llamada no tiene scope y falla antes de reportar. La primera instancia
del manejador permanece en caché pese al fallo de scope. Esta subclase mínima
solo CLI no inicializa las dependencias HTTP base; no es un ejemplo de
configuración de manejador HTTP.

## Consideraciones de rendimiento y concurrencia

- `Catch` crea un `asyncio.Lock` por instancia. Una doble comprobación dentro del lock protege la primera resolución del manejador frente a tareas concurrentes que usan ese lock en el mismo event loop; las llamadas con caché no lo toman.
- Lee el scope y el kernel en cada llamada; petición y excepción se pasan como argumentos, no se almacenan en el despachador.
- Espera el reporte antes de presentar. El módulo no crea tareas de fondo, renderizado paralelo, reporte por lotes ni reintentos.
- `toThrowable` convierte todos los argumentos a strings y conserva el traceback nativo. El trabajo depende de la cantidad de argumentos y del coste de cada `str`; retener la entidad puede retener frames y sus objetos referenciados.
- La exclusión consulta un `frozenset`; el mapeo HTTP recorre el MRO. La tabla privada tiene siete entradas y no es una API pública de registro.
- `report` y `handleCLI` son entradas asíncronas con llamadas síncronas y sin suspensión interna. Aquí no se delega el trabajo de logger/consola a un hilo worker.
- `handleHTTP` espera la presentación; el comportamiento compartido de manejador, configuración y respuestas depende de los componentes inyectados. No se añaden locks por petición alrededor del reporte o renderizado.
- Ninguno de estos métodos captura `BaseException` o `asyncio.CancelledError` lanzados por dependencias. La anotación `BaseException` describe la entrada, no una política de supresión de cancelaciones.

> ⚠️ No especificado en el código fuente: no se declara garantía de thread-safety ni de uso entre event loops para `Catch`, mutación del manejador o reemplazo concurrente de `dont_catch`.

> ⚠️ No especificado en el código fuente: no se declaran límites de CPU, memoria, tamaño del traceback o throughput; el módulo no proporciona cifras de benchmarks.

## Notas de compatibilidad

- `pyproject.toml` exige Python `>=3.14`. El módulo usa `asyncio`, anotaciones de unión, `Enum` y dataclasses con `kw_only=True`/`slots=True`; estas características por sí solas no justifican un mínimo específico de 3.14. El mínimo soportado es el declarado por el framework. `catch.py` y `base/handler.py` usan la evaluación diferida de anotaciones de Python 3.14 sin import future.
- No hay instalación adicional ni extra opcional `failure`. Los imports directos usan biblioteca estándar y módulos internos de Orionis; los 12 archivos no importan directamente paquetes de terceros.
- Los servicios relacionados usan dependencias incluidas por Orionis: `rich>=15.0.0,<16.0` (consola), `jinja2>=3.1.6,<4.0` (vistas), `msgspec>=0.21.1` (serialización HTTP JSON) y `pendulum>=3.2.0,<4.0` (fecha/hora del framework usada por servicios de salida relacionados). Son restricciones del manifiesto, no versiones instaladas exactas.
- El `Catch` del paquete raíz es el servicio concreto; `orionis.support.facades.catch.Catch` es la fachada registrada por separado. Los imports del manejador, contratos, entidad, enum y proveedor deben usar los paquetes indicados.
- `Catch.exception(request=None)` no permite manejar HTTP sin petición. Ignorar un tipo exacto devuelve `None`, no una respuesta predeterminada ni la excepción original relanzada.
- `Application.withExceptionHandler` valida una subclase de `IBaseExceptionHandler`, pese a la descripción de su docstring sobre `BaseExceptionHandler`. Si ya se cargó configuración compilada, retorna anticipadamente; `getExceptionHandler` exige completar el arranque. `Catch` no tiene método público para reemplazar o limpiar su instancia en caché.
- El mapeo protege el contenido HTTP público, pero no redacta el log base, el traceback CLI ni la página debug. El reporte base usa exactamente el primer argumento convertido a string; las respuestas debug reciben la excepción original.
- La validación HTTP/sesión, persistencia de sesión, saneamiento de errores SQL y envío de respuestas pertenecen a sus componentes, no a este módulo. El módulo no define clases de excepción propias.
