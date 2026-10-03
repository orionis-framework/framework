# orionis.failure

> Report exceptions and dispatch their presentation to the CLI or HTTP handler.

## Table of contents

- [Functional description](#functional-description)
- [API reference](#api-reference)
- [Usage examples](#usage-examples)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Functional description

`Catch` connects exceptions to the application's configured exception handler.
It reads the kernel from the current container scope, reports the exception,
then dispatches CLI or HTTP presentation. `BaseExceptionHandler` provides logging,
console traceback output and HTTP error responses; `Throwable` holds native
exception details without serializing them.

### Source inventory

All paths below are relative to `orionis/failure/`. These are all 12 Python files;
none of the initializers is empty.

| File | Defined API or package behavior |
|---|---|
| `__init__.py` | Lazily exports `Catch`; `__getattr__`, `__dir__`. |
| `catch.py` | `Catch.__init__`, async `Catch.exception`. |
| `base/__init__.py` | Exports `BaseExceptionHandler`. |
| `base/handler.py` | `BaseExceptionHandler.__init__`, `toThrowable`, `isExceptionIgnored`, async `report`, `handleCLI`, `handleHTTP`; private `_HTTP_STATUS_MAP`. |
| `contracts/__init__.py` | Exports `ICatch`, not `IBaseExceptionHandler`. |
| `contracts/catch.py` | `ICatch` and abstract async `exception`. |
| `contracts/handler.py` | `IBaseExceptionHandler` and its five abstract methods. |
| `entities/__init__.py` | Exports `Throwable`. |
| `entities/throwable.py` | Frozen, keyword-only, slotted `Throwable` dataclass. |
| `enums/__init__.py` | Exports `KernelContext`. |
| `enums/kernel_type.py` | `KernelContext(Enum)` with `CONSOLE` and `HTTP`. |
| `provider.py` | `CatchProvider.register`, async `CatchProvider.boot`. |

There are no ordinary module-level public functions or private helper methods.
The constructors and package hooks are the only explicit special methods.
Dataclass and Enum operations are generated or inherited, not handwritten APIs.

### Integration and execution order

Direct internal dependencies are `orionis.foundation` (`IApplication`),
`orionis.container` (`ServiceProvider`), `orionis.http` (`Request`,
`TransportAdapter`, `Response`, `DefaultResponses` and mapped exceptions),
`orionis.console` (`Console`), `orionis.logging` (`ILogger`), `orionis.auth`
(exceptions and `current_auth_context`), `orionis.support.facades.catch`
(the separate facade) and `orionis._exports` (lazy package exports).

`Catch.exception` performs these steps in order:

1. Resolve and cache `app.getExceptionHandler()` if no handler is cached.
2. Require `app.getCurrentScope()` and await `scope.get("kernel")`.
3. Await `app.call(handler, "report", exception=exception)`.
4. For `KernelContext.CONSOLE`, return the result of `handleCLI` through `app.call`.
5. For `KernelContext.HTTP`, return the result of `handleHTTP`, passing `request`.
6. For any other non-`None` context, return `None` after reporting.

The enum comparisons use identity (`is`), not string or integer equality.
Reporting's return value does not control dispatch: a `None` result from `report`
does not prevent `handleCLI` or `handleHTTP` from being called.

### Design decisions

- Contract/implementation separation: `ICatch` and `IBaseExceptionHandler` expose distinct dispatch and presentation responsibilities.
- Container-managed singleton: `CatchProvider` shares a `Catch` instance, including its cached handler, across calls.
- Lazy handler resolution: the first exception resolves the handler, even before checking the scope.
- Frozen, slotted dataclass: `Throwable` prevents field reassignment but retains the original mutable traceback reference.
- Exact-type ignore set: ignoring a base exception does not implicitly ignore its subclasses.
- MRO-based HTTP mapping: subclasses inherit the first mapped ancestor's public status and message.
- No declared `__slots__` on handlers, dispatcher or contracts: unlike `Throwable`, these instances have an instance dictionary.

## API reference

Signatures in `text` blocks reproduce source declarations, including `self`,
annotations and defaults. They are reference fragments, not runnable examples.
The `python` blocks under Usage examples are complete independent scripts.

> ⚠️ No especificado en el código fuente: `Catch`, `BaseExceptionHandler`, `ICatch`, `IBaseExceptionHandler` and `CatchProvider` have no own class docstring. The behavior below is established from their method bodies, method docstrings and declarations, not from an inherited class description.

### Catch

Import: `from orionis.failure import Catch` or
`from orionis.failure.catch import Catch`. This is the service, not the facade.
It inherits `ICatch`.

```text
	def __init__(self, app: IApplication) -> None:

	async def exception(
		self,
		exception: BaseException,
		request: Request | TransportAdapter | None = None,
	) -> Response | None:
```

- `app: IApplication`: supplies handler resolution, current scope and `call` with dependency injection. Construction stores it, initializes the handler cache to `None` and creates an `asyncio.Lock`; returns `None`.
- `exception: BaseException`: forwarded unchanged to `report` and the selected presentation method.
- `request: Request | TransportAdapter | None = None`: passed only to HTTP handling. The default is valid for console dispatch; the base HTTP handler requires a non-`None` object exposing `wantsJson()`.
- Return: `Response | None`; the base CLI handler returns `None`, the base HTTP handler returns a response or `None` when ignored. Custom handler results are returned without runtime type validation.
- Raises `RuntimeError` when scope is `None` (`No active scope found for context retrieval.`) or its kernel is `None` (`No kernel found in the current scope for context retrieval.`).
- Handler resolution, scope lookup and all `app.call` failures propagate. A failure in `report` prevents presentation; no fallback or retry wraps these calls.
- Effects: caches one successfully resolved handler; logs/renders through injected services. No automatic scope creation, exception re-raise, process exit or response transmission occurs here.

The concrete `Application.getExceptionHandler()` requires a booted application,
caches the handler **class**, then uses `build()` to create an instance on each
call. `Catch` separately retains the first instance it obtains. Failure during
resolution leaves its cache empty; a later call can resolve again.

### BaseExceptionHandler

Import: `from orionis.failure.base import BaseExceptionHandler` or
`from orionis.failure.base.handler import BaseExceptionHandler`.
It inherits `IBaseExceptionHandler`.

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

**Constructor.** `default_responses: DefaultResponses` renders HTTP errors and
debug pages; `application: IApplication` supplies `config("app.debug")`.
Stores both dependencies, returns `None`, and does not render or log anything.

**toThrowable.** `exception: BaseException` is converted into a `Throwable`.
Uses `exception.args or ("",)`, applies `str` to every argument, and uses the
first string as `message`. This is not necessarily `str(exception)`; for example,
`KeyError`'s quoting or a custom exception's `__str__` is not used to build it.
Stores `type(exception)` and the original `exception.__traceback__` reference.
No mutation, logging or explicit input validation; errors reading attributes or
stringifying arguments propagate.

**isExceptionIgnored.** `exception: BaseException` must be an exception instance;
otherwise raises `TypeError` with `Expected BaseException, got <type name>`.
Returns `type(exception) in self.dont_catch` as `bool`. No side effects.
The default empty `frozenset` ignores nothing. Replacing the class attribute
affects instances using that class attribute; subclasses can declare their own.

**report.** `exception: BaseException` is checked against `dont_catch`.
`log: ILogger` receives a synchronous `log.error` call formatted as
`[<exception class name>] <first stringified argument>`. Returns the converted
`Throwable`, or `None` without logging when ignored. No traceback, remaining
arguments or exception chain is passed to `log.error` by this method.
`TypeError` from the ignore check and conversion/logger failures propagate.
The coroutine contains no `await`; logging may perform synchronous I/O through
the supplied logger. Direct calls must supply `log`; `Catch` supplies it via DI.

**handleCLI.** `exception: BaseException` is checked against `dont_catch`.
`console: Console` receives `console.exception(exception)` unless ignored.
Returns `None` in either case; no exit code or process termination is requested.
`TypeError` from the ignore check and console failures propagate. There is no
`await` inside this coroutine. Direct calls must supply `console`; `Catch` uses DI.

**handleHTTP.** `exception: BaseException` is checked against `dont_catch` before
accessing `request: Request | TransportAdapter`. Ignored errors return `None`.
Otherwise calls `request.wantsJson()` and scans `type(exception).__mro__`:

| First mapped ancestor | HTTP status | Exact public content |
|---|---|---|
| `AuthenticationException` | 401 | `Unauthenticated` |
| `AuthorizationException` | 403 | `This action is unauthorized` |
| `RouteNotFound` | 404 | `Route not found` |
| `MethodNotAllowed` | 405 | `Method not allowed` |
| `PayloadTooLargeException` | 413 | `Payload too large` |
| `UnsupportedMediaTypeException` | 415 | `Unsupported media type` |
| `CSRFTokenMismatchException` | 419 | `CSRF token mismatch` |

Mapped errors call `await DefaultResponses.error` with the fixed content and
`expects_json=request.wantsJson()`, regardless of debug mode. Authentication
errors additionally receive `WWW-Authenticate: Bearer` if
`current_auth_context().guard == "token"`. The decision reads the authentication
context, not the request's Authorization header.

An unmapped error with falsy `application.config("app.debug")` uses status 500,
content `Internal Server Error` and the same JSON preference. `DefaultResponses`
produces `JSONResponse` with `{"message": content}` or renders HTML.

An unmapped error with truthy debug config calls
`await DefaultResponses.exception(..., status_code=500)`, which returns an
`HTMLResponse` even when `wantsJson()` was true. Passes the original exception
and request path/method. For an actual `TransportAdapter`, calls `path()` and
`method()`; otherwise reads `request.path` and `request.method` as properties.

No status is read from an exception's `code` or other custom attribute. No
validation-specific 422/redirect logic exists in this class. `ValidationException`
without separate HTTP-layer handling follows the unmapped-error path here.
No `Allow` header is added for `MethodNotAllowed` by this handler.

Raises `TypeError` for non-exception input. A non-ignored HTTP exception with
`request=None` raises `AttributeError` at `wantsJson()`. Request/config access,
authentication lookup, template rendering, response construction and header
failures propagate without a catch inside this method. Rendering may involve
template I/O; the response is returned, not sent.

### ICatch

Import: `from orionis.failure.contracts import ICatch` or its defining module
`orionis.failure.contracts.catch`. It inherits `abc.ABC`.

```text
	@abstractmethod
	async def exception(
		self,
		exception: BaseException,
		request: Request | TransportAdapter | None = None,
	) -> Response | None:
```

The parameters and return type match `Catch.exception`. The abstract method
contains only a docstring; it provides no dispatch or explicit exceptions.
`ICatch` cannot be instantiated until `exception` is implemented (`TypeError`
from ABC machinery).

> ⚠️ No especificado en el código fuente: the contract does not enforce reporting, scope behavior or the exceptions of third-party implementations.

### IBaseExceptionHandler

Import directly from `orionis.failure.contracts.handler`; it is not re-exported
by `orionis.failure.contracts`. It inherits `abc.ABC`.

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

`exception` is the source exception; `log` is the reporting logger; `console`
is the CLI output dependency; `request` provides HTTP request context.
`toThrowable` returns structured details, `isExceptionIgnored` returns an ignore
decision, `report` returns details or `None`, `handleCLI` returns `None`, and
`handleHTTP` returns a response or `None`. All five methods are abstract and
docstring-only. Missing implementations prevent instantiation with `TypeError`.
The contract annotates `console` as `IConsole`; the concrete handler uses `Console`.

> ⚠️ No especificado en el código fuente: abstract bodies do not prescribe side effects, HTTP mappings or exceptions for custom handlers.

### Throwable

Import: `from orionis.failure.entities import Throwable` or
`from orionis.failure.entities.throwable import Throwable`.

The literal declaration is shown because the constructor is generated by
`dataclass`, not declared with `def`:

```text
@dataclass(frozen=True, kw_only=True, slots=True)
class Throwable:
	classtype: type
	message: str
	args: tuple
	traceback: TracebackType | None = None
```

Construct with keyword arguments. `classtype: type`, `message: str` and
`args: tuple` are required; `traceback: TracebackType | None` defaults to `None`.
`BaseExceptionHandler.toThrowable` supplies a tuple of strings, but the field's
actual annotation is bare `tuple`, not `tuple[str, ...]`.

Construction returns a new `Throwable`; there is no custom validation or I/O.
Python rejects missing required or positional constructor arguments with
`TypeError`. Reassigning a declared field raises `dataclasses.FrozenInstanceError`.
Frozen fields do not deeply freeze referenced objects, and storing a traceback
retains access to its frames. The entity does not inherit `BaseEntity`, expose
`toDict()`/`toJson()`, format a traceback or include explicit cause/context fields.

### KernelContext

Import: `from orionis.failure.enums import KernelContext` or
`from orionis.failure.enums.kernel_type import KernelContext`.

```text
class KernelContext(Enum):
	CONSOLE = auto()
	HTTP = auto()
```

The two standard Enum members have values 1 and 2 respectively. No custom
methods or constructor are declared. Standard Enum lookup can raise `ValueError`
for an unknown value and `KeyError` for an unknown member name. `Catch` requires
the member objects for dispatch: `"HTTP"`, `"http"` and `2` are not HTTP contexts
for its identity checks. This module does not write the scope's `"kernel"` key.

### CatchProvider

Import: `from orionis.failure.provider import CatchProvider`.
It inherits `orionis.container.providers.service_provider.ServiceProvider` and
is registered in `orionis.foundation.core_providers` as an eager provider.

Inherited constructor declaration from `ServiceProvider`:

```text
	def __init__(
		self,
		app: IApplication,
	) -> None:
```

`app: IApplication` is stored as `self.app`; construction returns `None`.

```text
	def register(self) -> None:

	async def boot(self) -> None:
```

`register()` takes no additional parameters, returns `None` and calls
`self.app.singleton(ICatch, Catch, alias="x-orionis-ICatch")`. It does not register
`IBaseExceptionHandler` or build a handler. Registration failures propagate.

`boot()` takes no additional parameters, returns `None` and awaits
`CatchFacade.pin()`, mutating the facade's shared pinned state. Resolution/pinning
failures propagate. Registering the provider alone does not pin the facade.
Use `await CatchFacade.exception(...)` when calling through the facade; the
underlying operation is async even after pinning.

### Package hooks

Defined in `orionis.failure.__init__`:

```text
def __getattr__(name: str) -> object:

def __dir__() -> list[str]:
```

`__getattr__` accepts `name: str`, delegates to `orionis._exports.resolve_export`
and returns the exported object. Access to `Catch` imports its defining module
on demand and caches the export in the package namespace. Unknown names raise
`AttributeError`; import failures propagate. `__dir__` takes no arguments and
returns sorted loaded names plus declared exports as `list[str]`, without
resolving the exports.

## Usage examples

Each block is an independent Python 3.14+ script. The HTTP example uses a small
configuration object and in-memory templates so it needs neither an application
bootstrap nor a web server. These explicit fixtures are not new framework APIs.

### Handle an HTTP error

Build the real `BaseExceptionHandler`, `DefaultResponses`, `Directory` and
`Jinja2Engine`; pass an actual ASGI transport adapter and inspect the returned
response. A mapped error hides the supplied private message even in debug mode.

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

### Preserve a traceback and handle immutability

`Throwable` can be constructed without DI. Catching the reassignment error does
not discard the stored traceback or change its message.

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

### Dispatch through a container scope

Use the real `Container` scope and `call()` injection mechanism with a CLI-only
custom handler. Its reporting and presentation override the base behavior, so
this example writes to standard output rather than configuring `ILogger` or
`Console`. Only inherited `toThrowable` is used; the base HTTP renderer is not
used. In a real application, select an importable handler class with
`Application.withExceptionHandler()` before bootstrap configuration is locked.

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

The final call has no scope and raises before reporting. The first handler
instance remains cached despite that scope failure. This minimal CLI-only
subclass does not initialize the base HTTP dependencies and is not an HTTP
handler configuration example.

## Performance and concurrency considerations

- `Catch` creates one `asyncio.Lock` per instance. A double check inside the lock protects its first handler resolution against concurrent tasks using that lock on the same event loop; cached calls skip it.
- Scope and kernel are read on every call; request and exception are passed as call arguments, not stored on the dispatcher.
- Reporting is awaited before presentation. There is no background task, parallel rendering, batch reporting or retry in this module.
- `toThrowable` stringifies every argument and retains the native traceback. Its work scales with argument count and the cost of each `str` conversion; holding the entity can retain traceback frames and their referenced objects.
- Ignore lookup uses a `frozenset`; HTTP status lookup scans the exception's MRO. The private status table has seven entries and is not a public registration API.
- `report` and `handleCLI` are async entry points containing synchronous calls and no internal suspension. Their logger/console work is not moved to a worker thread here.
- `handleHTTP` awaits rendering; shared handler/configuration/response-service behavior depends on the injected components. No per-request locks are added around reporting or rendering.
- None of these methods catches `BaseException` or `asyncio.CancelledError` raised by dependencies. The `BaseException` annotation is input acceptance, not a cancellation suppression policy.

> ⚠️ No especificado en el código fuente: there is no declared thread-safety or cross-event-loop guarantee for `Catch`, handler mutation or concurrent replacement of `dont_catch`.

> ⚠️ No especificado en el código fuente: no CPU, memory, traceback-size or throughput limits are declared; the module provides no benchmark figures.

## Compatibility notes

- `pyproject.toml` requires Python `>=3.14`. This module uses `asyncio`, union annotations, `Enum`, and dataclasses with `kw_only=True`/`slots=True`; those features alone do not justify a 3.14-specific minimum. The supported minimum is the framework's declared requirement. `catch.py` and `base/handler.py` use Python 3.14's deferred annotation evaluation without a future import.
- There is no additional installation requirement or optional `failure` extra. Direct imports use the standard library and internal Orionis modules; there are no direct third-party imports in the 12 module files.
- Related services use dependencies already included by Orionis: `rich>=15.0.0,<16.0` (console), `jinja2>=3.1.6,<4.0` (view rendering), `msgspec>=0.21.1` (HTTP JSON serialization) and `pendulum>=3.2.0,<4.0` (framework date/time used by related output services). These are manifest constraints, not exact installed versions.
- Root package `Catch` is the concrete service; `orionis.support.facades.catch.Catch` is the separately registered facade. Handler, contracts, entity, enum and provider imports must use the packages listed above.
- `Catch.exception(request=None)` does not make HTTP handling request-free. Ignoring an exact type returns `None`, not a default response and not a re-raised original exception.
- `Application.withExceptionHandler` validates an `IBaseExceptionHandler` subclass, despite its docstring wording about `BaseExceptionHandler`. When compiled configuration is already loaded it returns early; `getExceptionHandler` requires bootstrap completion. `Catch` has no public method to replace or clear its cached instance.
- Mapping protects public HTTP content but does not redact the base reporting log, CLI traceback or debug page. Base reporting uses the first exception argument exactly as stringified; debug responses receive the original exception.
- HTTP/session validation, session persistence, SQL error sanitization and response sending belong to their respective components, not this module. The module itself defines no custom exception classes.
