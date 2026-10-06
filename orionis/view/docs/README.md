# orionis.view

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.view initializer exports 15 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.view/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| OrionisBytecodeCache | from orionis.view import OrionisBytecodeCache | [cache.py](../cache.py) | OrionisBytecodeCache | Public declaration without a class or function docstring. |
| OrionisBytecodeCache.getCacheKey | from orionis.view import OrionisBytecodeCache | [cache.py](../cache.py) | def getCacheKey(self, name: str, filename: str / None) -> str | Convert a template name into a human-readable cache key. Flattening separators and dropping the extension is a lossy transformation, so distinct templates such as ``mail/welcome.html`` and ``mail/welcome.j2`` would share a single cache file. A short digest of the untouched name is appended to keep the mapping injective while the stem stays readable. Parameters ---------- name : str Template identifier (e.g. ``'users/index.html'``). filename : str or None, optional Absolute path on disk; unused here. Returns ------- str Sanitised key used as the cache filename stem. |
| IViewEngine | from orionis.view import IViewEngine | [contracts/engine.py](../contracts/engine.py) | IViewEngine | Contract for view engine implementations. All rendering engines registered with the view system must implement this interface so that the rest of the framework remains decoupled from any concrete template technology. |
| IViewEngine.render | from orionis.view import IViewEngine | [contracts/engine.py](../contracts/engine.py) | async def render(self, template: str, context: dict[str, Any]) -> str | Render a template with the supplied context and return HTML. Parameters ---------- template : str Template identifier. Engines are free to interpret this string (e.g. dot notation ``'users.index'`` or a bare filename). context : dict[str, Any] Mapping of variable names to values made available inside the template during rendering. Returns ------- str The rendered HTML string produced by the engine. Raises ------ ViewTemplateNotFoundException When the requested template file cannot be located. ViewRenderException When the template engine fails to render the template. |
| IViewEnvironment | from orionis.view import IViewEnvironment | [contracts/environment.py](../contracts/environment.py) | IViewEnvironment | Contract for the view-environment wrapper. The implementation is the sole authority for configuring the underlying template engine's environment (loaders, caches, globals, filters, tests, and extensions). No other class should access the engine environment directly. |
| IViewEnvironment.addGlobal | from orionis.view import IViewEnvironment | [contracts/environment.py](../contracts/environment.py) | def addGlobal(self, name: str, value: Any) -> None | Register a global variable or callable available in all templates. Parameters ---------- name : str Identifier used to reference the value inside templates. value : Any Value or callable to expose as a template global. Returns ------- None |
| IViewEnvironment.addFilter | from orionis.view import IViewEnvironment | [contracts/environment.py](../contracts/environment.py) | def addFilter(self, name: str, callback: Callable) -> None | Register a filter callable that templates can apply with ``/``. Parameters ---------- name : str Filter name used inside template expressions (e.g. ``/ slug``). callback : Callable Function applied to the piped value. The first argument receives the value being filtered. Returns ------- None |
| IViewEnvironment.addTest | from orionis.view import IViewEnvironment | [contracts/environment.py](../contracts/environment.py) | def addTest(self, name: str, callback: Callable) -> None | Register a test callable used in Jinja2 ``is`` expressions. Parameters ---------- name : str Test name used in template expressions (e.g. ``is odd``). callback : Callable Function that receives the tested value and returns a bool. Returns ------- None |
| IViewEnvironment.addExtension | from orionis.view import IViewEnvironment | [contracts/environment.py](../contracts/environment.py) | def addExtension(self, extension: Any) -> None | Register a Jinja2 extension class with the environment. Parameters ---------- extension : Any A Jinja2 :class:`Extension` subclass or its dotted import path. Returns ------- None Raises ------ ViewException When the extension cannot be registered. |
| IViewEnvironment.getJinjaEnvironment | from orionis.view import IViewEnvironment | [contracts/environment.py](../contracts/environment.py) | def getJinjaEnvironment(self) -> Any | Return the underlying Jinja2 :class:`Environment` instance. Access is intentionally restricted to this method so that all configuration changes flow through the typed helpers above. Returns ------- jinja2.Environment The configured Jinja2 environment. |
| IViewFactory | from orionis.view import IViewFactory | [contracts/factory.py](../contracts/factory.py) | IViewFactory | Contract for the view factory. Callers use this interface to render named templates and receive fully formed :class:`HTMLResponse` objects ready to return from HTTP controllers. |
| IViewFactory.make | from orionis.view import IViewFactory | [contracts/factory.py](../contracts/factory.py) | def make(self, template: str, **context) -> PendingView | Prepare a template render as an awaitable, chainable response. Parameters ---------- template : str Template name using dot notation (e.g. ``'users.index'``) or a direct path relative to a configured template directory. **context : Any Keyword arguments are forwarded as template variables. Returns ------- PendingView Awaitable proxy that resolves to an :class:`HTMLResponse` and accepts chained response mutators such as ``withFlash()``. Raises ------ ViewTemplateNotFoundException When the requested template file cannot be located. ViewRenderException When the template engine fails during rendering. |
| Jinja2Engine | from orionis.view import Jinja2Engine | [engine.py](../engine.py) | Jinja2Engine | Jinja2-based implementation of :class:`IViewEngine`. Converts dot-notation template names to filesystem paths and delegates all rendering to Jinja2's async rendering pipeline (``render_async``). The synchronous ``render`` method of Jinja2 is **never** called from this class. |
| Jinja2Engine.render | from orionis.view import Jinja2Engine | [engine.py](../engine.py) | async def render(self, template: str, context: dict[str, Any]) -> str | Render a template asynchronously using Jinja2. Dot-notation identifiers are converted to slash-delimited paths with a ``.html`` suffix automatically appended when the name carries no extension (e.g. ``'users.index'`` → ``'users/index.html'``). Parameters ---------- template : str Template identifier using dot notation or a direct relative path. A ``.html`` suffix is appended when absent. context : dict[str, Any] Variables made available inside the template during rendering. Returns ------- str Rendered HTML string. Raises ------ ViewTemplateNotFoundException When the template file cannot be located by the configured loaders. ViewRenderException When Jinja2 raises any error during rendering. |
| ViewEnvironment | from orionis.view import ViewEnvironment | [environment.py](../environment.py) | ViewEnvironment | Encapsulate and configure a Jinja2 :class:`Environment` instance. This is the single authorised class for configuring the underlying template engine. All loaders, caches, globals, filters, tests and extensions must be registered through the public methods of this class. The Jinja2 :class:`Environment` is built once during construction and stored internally; no other class may access it directly except through :meth:`getJinjaEnvironment`. |
| ViewEnvironment.addGlobal | from orionis.view import ViewEnvironment | [environment.py](../environment.py) | def addGlobal(self, name: str, value: Any) -> None | Register a global variable or callable in all templates. Parameters ---------- name : str Identifier used to reference the value inside templates. value : Any Value or callable to expose as a template global. Returns ------- None |
| ViewEnvironment.addFilter | from orionis.view import ViewEnvironment | [environment.py](../environment.py) | def addFilter(self, name: str, callback: Callable) -> None | Register a filter callable that templates can apply with ``/``. Parameters ---------- name : str Filter name referenced inside template expressions (e.g. ``/ slug``). callback : Callable Function applied to the piped value. Returns ------- None |
| ViewEnvironment.addTest | from orionis.view import ViewEnvironment | [environment.py](../environment.py) | def addTest(self, name: str, callback: Callable) -> None | Register a test callable used in Jinja2 ``is`` expressions. Parameters ---------- name : str Test name referenced inside template ``is`` expressions. callback : Callable Function receiving the tested value and returning a bool. Returns ------- None |
| ViewEnvironment.addExtension | from orionis.view import ViewEnvironment | [environment.py](../environment.py) | def addExtension(self, extension: Any) -> None | Register a Jinja2 extension class with the environment. Parameters ---------- extension : Any A Jinja2 :class:`Extension` subclass or its dotted import path. Returns ------- None Raises ------ ViewException When the extension cannot be registered by Jinja2. |
| ViewEnvironment.getJinjaEnvironment | from orionis.view import ViewEnvironment | [environment.py](../environment.py) | def getJinjaEnvironment(self) -> jinja2.Environment | Return the configured Jinja2 :class:`Environment` instance. Returns ------- jinja2.Environment The internal Jinja2 environment. Treat as read-only outside this class; all mutations must flow through the typed helpers. |
| ViewException | from orionis.view import ViewException | [exceptions.py](../exceptions.py) | ViewException | Base exception for all view-system errors. All specialised view exceptions inherit from this class, allowing callers to catch the entire view-exception hierarchy with a single ``except ViewException`` clause. |
| ViewRenderException | from orionis.view import ViewRenderException | [exceptions.py](../exceptions.py) | ViewRenderException | Raised when a template fails to render. Typically wraps a Jinja2 :class:`TemplateError` and preserves the original cause as the ``__cause__`` of the exception chain. |
| ViewTemplateNotFoundException | from orionis.view import ViewTemplateNotFoundException | [exceptions.py](../exceptions.py) | ViewTemplateNotFoundException | Raised when the requested template file cannot be located. Wraps a Jinja2 :class:`TemplateNotFound` and preserves the original cause as the ``__cause__`` of the exception chain. |
| ViewRouteException | from orionis.view import ViewRouteException | [exceptions.py](../exceptions.py) | ViewRouteException | Raised when the ``route()`` template global cannot build a URL. Signals either an unknown route name or a path parameter left without a value. |
| CsrfExtension | from orionis.view import CsrfExtension | [extensions/csrf.py](../extensions/csrf.py) | CsrfExtension | Provide the ``{% csrf %}`` statement tag. The tag is a zero-argument shortcut for ``{{ csrf_field() }}``: it renders the hidden input holding the current CSRF token, so forms need no explicit call to the template global. |
| CsrfExtension.parse | from orionis.view import CsrfExtension | [extensions/csrf.py](../extensions/csrf.py) | def parse(self, parser: Parser) -> nodes.Output | Compile the ``{% csrf %}`` tag into an output node. Parameters ---------- parser : Parser Jinja2 parser positioned on the tag name token. Returns ------- nodes.Output Node emitting the hidden CSRF input at render time. |
| ViewFactory | from orionis.view import ViewFactory | [factory.py](../factory.py) | ViewFactory | Render named templates and return :class:`HTMLResponse` objects. :class:`ViewFactory` is the primary entry-point for controllers and other HTTP-layer code that needs to produce HTML responses from templates. It delegates all rendering work to the bound :class:`IViewEngine` and wraps the output in a framework-native :class:`HTMLResponse`. |
| ViewFactory.make | from orionis.view import ViewFactory | [factory.py](../factory.py) | def make(self, template: str, **context) -> PendingView | Prepare a template render as an awaitable, chainable response. Parameters ---------- template : str Template name using dot notation (e.g. ``'users.index'``) or a relative path (e.g. ``'users/index.html'``). **context : Any Keyword arguments forwarded as template variables. Returns ------- PendingView Awaitable proxy that renders the template on ``await`` and accepts chained response mutators such as ``withInput()``, ``withErrors()``, ``withFlash()``, ``withCookie()`` or ``withoutCookie()``. Raises ------ ViewTemplateNotFoundException When the view file cannot be located. ViewRenderException When rendering fails for any reason. |
| ErrorBag | from orionis.view import ErrorBag | [globals/errors.py](../globals/errors.py) | ErrorBag | Read-only view over the validation errors flashed for this request. Exposed to templates as the ``errors`` global. Every method is a coroutine, which Jinja2 awaits transparently in async environments:: {% if errors.any() %}{{ errors.first('email') }}{% endif %} |
| ErrorBag.all | from orionis.view import ErrorBag | [globals/errors.py](../globals/errors.py) | async def all(self) -> dict[str, list[str]] | Return every error grouped by field. Returns ------- dict[str, list[str]] Field-indexed error messages. |
| ErrorBag.any | from orionis.view import ErrorBag | [globals/errors.py](../globals/errors.py) | async def any(self) -> bool | Report whether at least one field failed validation. Returns ------- bool ``True`` when the bag holds any message. |
| ErrorBag.has | from orionis.view import ErrorBag | [globals/errors.py](../globals/errors.py) | async def has(self, field: str) -> bool | Report whether *field* has at least one error. Parameters ---------- field : str Form field name. Returns ------- bool ``True`` when the field failed validation. |
| ErrorBag.get | from orionis.view import ErrorBag | [globals/errors.py](../globals/errors.py) | async def get(self, field: str) -> list[str] | Return every message recorded for *field*. Parameters ---------- field : str Form field name. Returns ------- list[str] Messages for the field, empty when it is valid. |
| ErrorBag.first | from orionis.view import ErrorBag | [globals/errors.py](../globals/errors.py) | async def first(self, field: str / None) -> str | Return the first message for *field*, or the first of any field. Parameters ---------- field : str / None, optional Form field name. When omitted, the first message of the whole bag is returned, which suits a single summary line. Returns ------- str The message, or an empty string when there is none. |
| PendingView | from orionis.view import PendingView | [pending.py](../pending.py) | PendingView | Awaitable, chainable result of :meth:`IViewFactory.make`. Rendering is deferred until the object is awaited, so response mutators such as ``withInput()``, ``withErrors()``, ``withFlash()`` or ``withCookie()`` can be chained directly on the ``make()`` call:: return await View.make("auth.login").withErrors(errors) Every attribute that exists on :class:`HTMLResponse` is accepted and replayed on the real response once the template has been rendered. |
| PendingView.withFlash | from orionis.view import PendingView | [pending.py](../pending.py) | def withFlash(self, key: str, value: Any) -> PendingView | Flash a status message into the session before rendering. Writing happens ahead of rendering so this very view can read the value back through the ``flash()`` global, and it remains available for the next request. Parameters ---------- key : str Flash data key. value : Any, optional Value to flash. Returns ------- PendingView The same pending view, allowing fluent chaining. |
| PendingView.withInput | from orionis.view import PendingView | [pending.py](../pending.py) | def withInput(self, values: Mapping[str, Any]) -> PendingView | Flash the submitted payload so ``old()`` can repopulate the form. Credential-like fields such as ``password`` are stripped. Parameters ---------- values : Mapping[str, Any] Submitted form payload to remember. Returns ------- PendingView The same pending view, allowing fluent chaining. |
| PendingView.withErrors | from orionis.view import PendingView | [pending.py](../pending.py) | def withErrors(self, errors: Mapping[str, Any] / Exception) -> PendingView | Flash validation errors so the ``errors`` global can read them. Parameters ---------- errors : Mapping[str, Any] / Exception Mapping of field to message(s), or a validation exception. Returns ------- PendingView The same pending view, allowing fluent chaining. |
| PendingView.render | from orionis.view import PendingView | [pending.py](../pending.py) | async def render(self) -> HTMLResponse | Render the template into a fully formed :class:`HTMLResponse`. Returns ------- HTMLResponse An HTTP response whose body is the rendered HTML content. Raises ------ ViewTemplateNotFoundException When the view file cannot be located. ViewRenderException When rendering fails for any reason. |
| ViewServiceProvider | from orionis.view import ViewServiceProvider | [provider.py](../provider.py) | ViewServiceProvider | Register and boot the view system into the application container. Registration phase ------------------ Binds :class:`IViewEnvironment` → :class:`ViewEnvironment`, :class:`IViewEngine` → :class:`Jinja2Engine`, and :class:`IViewFactory` → :class:`ViewFactory` as singletons. Boot phase ---------- Registers template globals, filters, and extensions with the :class:`ViewEnvironment` singleton, then pins the :class:`View` facade for zero-resolution access on the hot path. |
| ViewServiceProvider.register | from orionis.view import ViewServiceProvider | [provider.py](../provider.py) | def register(self) -> None | Bind view services as singletons in the application container. Returns ------- None |
| ViewServiceProvider.boot | from orionis.view import ViewServiceProvider | [provider.py](../provider.py) | async def boot(self) -> None | Register globals, filters, and extensions; then pin the facade. Returns ------- None |

## Usage examples

    from orionis.view import OrionisBytecodeCache

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
