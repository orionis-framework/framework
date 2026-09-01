from __future__ import annotations
from typing import TYPE_CHECKING, Any, ClassVar, Self
import msgspec
from orionis.console.output.http_request import HTTPRequestPrinter
from orionis.failure.enums.kernel_type import KernelContext
from orionis.http import kernel as kernel_module
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.default.responses import DefaultResponses
from orionis.http.enums.interfaces import Interface
from orionis.http.kernel import KernelHTTP
from orionis.http.layer.web.csrf_token import CSRFTokenMiddleware
from orionis.http.layer.web.start_session import StartSessionMiddleware
from orionis.http.middleware import BaseMiddleware
from orionis.http.payload.body import BodyStream
from orionis.http.request import Request
from orionis.http.responses import JSONResponse, Response
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.loader import RouteLoader
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exceptions.validation import ValidationException
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_MODULE: str = __name__


# ---------------------------------------------------------------------------
# Route handlers resolved by the kernel dispatch tables.
# ---------------------------------------------------------------------------


def web_handler() -> Response:
    """
    Return a plain response for a web-group route.

    Returns
    -------
    Response
        Response carrying a fixed marker body.
    """
    return Response(content="web")


def api_handler() -> Response:
    """
    Return a plain response for an API-group route.

    Returns
    -------
    Response
        Response carrying a fixed marker body.
    """
    return Response(content="api")


def dict_handler() -> dict[str, int]:
    """
    Return a mapping the kernel must coerce into a JSON response.

    Returns
    -------
    dict[str, int]
        Payload serialised by the kernel.
    """
    return {"answer": 42}


class _Payload(msgspec.Struct):
    """Structured payload returned by a handler."""

    name: str


def struct_handler() -> _Payload:
    """
    Return a structured payload the kernel must coerce into JSON.

    Returns
    -------
    _Payload
        Payload serialised by the kernel.
    """
    return _Payload(name="orionis")


def invalid_handler() -> None:
    """
    Return nothing so the kernel rejects the handler result.

    Returns
    -------
    None
        Deliberately not a response object.
    """
    return


def failing_handler() -> Response:
    """
    Raise a domain error to exercise the failure handler.

    Returns
    -------
    Response
        Never returned; the call always raises.

    Raises
    ------
    RuntimeError
        Always.
    """
    error_msg = "handler exploded"
    raise RuntimeError(error_msg)


def validation_handler() -> Response:
    """
    Raise a validation failure to exercise the validation branches.

    Returns
    -------
    Response
        Never returned; the call always raises.

    Raises
    ------
    ValidationException
        Always.
    """
    raise ValidationException(
        ValidationFailure(field="email", rule="pattern", message="Invalid."),
    )


def fallback_function() -> Response:
    """
    Return the response produced by a callable fallback.

    Returns
    -------
    Response
        Response carrying a fixed marker body.
    """
    return Response(content="fallback-function")


class _Controller:
    """Controller resolved through the class dispatch table."""

    __slots__ = ()

    def show(self) -> Response:
        """
        Return the response produced by a controller action.

        Returns
        -------
        Response
            Response carrying a fixed marker body.
        """
        return Response(content="controller")


class _FallbackController:
    """Controller registered as the route fallback."""

    __slots__ = ()

    def handle(self) -> Response:
        """
        Return the response produced by the fallback controller.

        Returns
        -------
        Response
            Response carrying a fixed marker body.
        """
        return Response(content="fallback-controller")


class _BrokenFallbackController:
    """Fallback controller that does not honour the response contract."""

    __slots__ = ()

    def handle(self) -> None:
        """
        Return nothing so the kernel rejects the fallback result.

        Returns
        -------
        None
            Deliberately not a response object.
        """
        return


# ---------------------------------------------------------------------------
# Middleware doubles.
# ---------------------------------------------------------------------------


class _RecordingMiddleware(BaseMiddleware):
    """Route middleware recording every invocation."""

    calls: ClassVar[list[str]] = []

    __slots__ = ()

    async def handle(self, request: Request, call_next: object) -> Response:
        """
        Record the visit and continue through the pipeline.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        call_next : object
            Pipeline continuation.

        Returns
        -------
        Response
            Response produced downstream, tagged with a marker header.
        """
        _RecordingMiddleware.calls.append(request.path)
        response = await call_next()
        response.setHeader("x-route-middleware", "1")
        return response


class _SessionMiddlewareDouble(BaseMiddleware):
    """Stand-in for the session middleware installed by the kernel."""

    calls: ClassVar[list[str]] = []

    __slots__ = ()

    async def handle(self, request: Request, call_next: object) -> Response:
        """
        Record the visit and continue through the pipeline.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        call_next : object
            Pipeline continuation.

        Returns
        -------
        Response
            Response produced downstream.
        """
        _SessionMiddlewareDouble.calls.append(request.path)
        return await call_next()


class _DoubleNextMiddleware(BaseMiddleware):
    """Middleware that wrongly advances the pipeline twice."""

    __slots__ = ()

    async def handle(self, _request: Request, call_next: object) -> Response:
        """
        Advance the pipeline twice from the same layer.

        Parameters
        ----------
        _request : Request
            Incoming HTTP request.
        call_next : object
            Pipeline continuation.

        Returns
        -------
        Response
            Never returned; the second call always raises.
        """
        await call_next()
        return await call_next()


# ---------------------------------------------------------------------------
# Application and transport doubles.
# ---------------------------------------------------------------------------


class _StubScope:
    """Container scope double recording per-request bindings."""

    __slots__ = ("entries", "tags")

    def __init__(self) -> None:
        """Initialise the two recording dictionaries."""
        self.entries: dict[object, object] = {}
        self.tags: dict[str, object] = {}

    async def __aenter__(self) -> Self:
        """
        Enter the scope.

        Returns
        -------
        Self
            The scope itself.
        """
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        """
        Leave the scope without swallowing exceptions.

        Returns
        -------
        bool
            Always ``False``.
        """
        return False

    def set(self, key: str, value: object) -> None:
        """
        Tag the scope with a keyed value.

        Parameters
        ----------
        key : str
            Tag name.
        value : object
            Tag value.
        """
        self.tags[key] = value

    def __setitem__(self, key: object, value: object) -> None:
        """
        Register a per-request instance.

        Parameters
        ----------
        key : object
            Contract used as the binding key.
        value : object
            Instance bound for this request.
        """
        self.entries[key] = value


class _StubDefaultResponses:
    """Default response factory double returning JSON payloads."""

    __slots__ = ("calls",)

    def __init__(self) -> None:
        """Initialise the call recorder."""
        self.calls: list[tuple[int, object, bool]] = []

    def error(
        self,
        status_code: int,
        content: object,
        *,
        expects_json: bool,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        """
        Build a JSON error response mirroring the real factory contract.

        Parameters
        ----------
        status_code : int
            HTTP status code to report.
        content : object
            Error payload.
        expects_json : bool
            Whether the caller asked for a JSON payload.
        headers : dict[str, str] | None, optional
            Extra headers.

        Returns
        -------
        JSONResponse
            Response carrying the given payload.
        """
        self.calls.append((status_code, content, expects_json))
        payload = content if isinstance(content, dict) else {"message": content}
        return JSONResponse(
            content=payload,
            status_code=status_code,
            headers=headers,
        )


class _StubCatch:
    """Failure handler double translating exceptions into responses."""

    __slots__ = ("handled",)

    def __init__(self) -> None:
        """Initialise the recorder of handled exceptions."""
        self.handled: list[BaseException] = []

    async def exception(self, exc: BaseException, _request: object) -> Response:
        """
        Record the exception and answer with a ``500`` response.

        Parameters
        ----------
        exc : BaseException
            Exception raised while processing the request.
        _request : object
            Request or transport adapter for the failed request.

        Returns
        -------
        Response
            Response reporting the failure.
        """
        self.handled.append(exc)
        return Response(content=str(exc), status_code=500)


class _StubRouteLoader:
    """Route loader double publishing pre-built compiled routes."""

    __slots__ = ("_fallback", "_routes")

    def __init__(self, routes: dict[str, dict], fallback: tuple | None) -> None:
        """
        Store the compiled routes and the fallback descriptor.

        Parameters
        ----------
        routes : dict[str, dict]
            Compiled route tables grouped by HTTP method.
        fallback : tuple | None
            Registered fallback handler.
        """
        self._routes = routes
        self._fallback = fallback

    def load(self) -> dict[str, dict]:
        """
        Return the compiled route tables.

        Returns
        -------
        dict[str, dict]
            Route tables consumed by the resolver.
        """
        return self._routes

    @property
    def fallback(self) -> tuple | None:
        """
        Return the registered fallback handler.

        Returns
        -------
        tuple | None
            Fallback descriptor, or ``None`` when unset.
        """
        return self._fallback


class _StubRequestPrinter:
    """Debug request printer double recording its activity."""

    __slots__ = ("enabled", "printed", "timers")

    def __init__(self) -> None:
        """Initialise the activity recorders."""
        self.enabled: bool = False
        self.printed: list[Response] = []
        self.timers: int = 0

    def setEnabled(self, *, enabled: bool) -> None:
        """
        Store the requested activation flag.

        Parameters
        ----------
        enabled : bool
            Whether the printer should log requests.
        """
        self.enabled = enabled

    def startTimer(self) -> None:
        """Record the start of a request timer."""
        self.timers += 1

    def printRequest(self, _adapter: object, response: Response) -> None:
        """
        Record the response that would be logged.

        Parameters
        ----------
        _adapter : object
            Transport adapter for the request.
        response : Response
            Response about to be sent.
        """
        self.printed.append(response)


class _StubResponseAdapter:
    """Response adapter double returning the response it would send."""

    __slots__ = ("sent",)

    def __init__(self) -> None:
        """Initialise the recorder of sent responses."""
        self.sent: list[Response] = []

    async def send(
        self,
        _adapter: object,
        response: Response,
        *_transport: object,
    ) -> Response:
        """
        Record and return the response instead of writing it out.

        Parameters
        ----------
        _adapter : object
            Transport adapter for the request.
        response : Response
            Response to send.
        *_transport : object
            Transport specific callables or protocol objects.

        Returns
        -------
        Response
            The very same response.
        """
        self.sent.append(response)
        return response


class _StubApp:
    """Application double resolving the kernel collaborators."""

    __slots__ = ("builds", "config_data", "debug", "maintenance", "scopes")

    def __init__(
        self,
        builds: dict[type, object],
        config_data: dict[str, object],
        *,
        debug: bool = False,
        maintenance: bool = False,
    ) -> None:
        """
        Store the collaborators and configuration served to the kernel.

        Parameters
        ----------
        builds : dict[type, object]
            Pre-built instances returned by ``build()``.
        config_data : dict[str, object]
            Configuration sections served by ``config()``.
        debug : bool, optional
            Whether the application runs in debug mode.
        maintenance : bool, optional
            Whether the application is under maintenance.
        """
        self.builds = builds
        self.config_data = config_data
        self.debug = debug
        self.maintenance = maintenance
        self.scopes: list[_StubScope] = []

    async def build(self, concrete: type) -> object:
        """
        Return the registered double, or construct the class directly.

        Parameters
        ----------
        concrete : type
            Class requested by the kernel.

        Returns
        -------
        object
            Instance served to the kernel.
        """
        registered = self.builds.get(concrete)
        if registered is not None:
            return registered
        return concrete()

    def config(self, key: str) -> object:
        """
        Return one configuration section.

        Parameters
        ----------
        key : str
            Configuration path requested by the kernel.

        Returns
        -------
        object
            Configuration section, or ``None`` when unknown.
        """
        return self.config_data.get(key)

    def isDebug(self) -> bool:
        """
        Report whether the application runs in debug mode.

        Returns
        -------
        bool
            ``True`` when request logging must be active.
        """
        return self.debug

    def underMaintenance(self) -> bool:
        """
        Report whether the application is under maintenance.

        Returns
        -------
        bool
            ``True`` when every request must be rejected.
        """
        return self.maintenance

    def beginScope(self) -> _StubScope:
        """
        Open a per-request container scope.

        Returns
        -------
        _StubScope
            Freshly created scope double.
        """
        scope = _StubScope()
        self.scopes.append(scope)
        return scope

    async def invoke(self, func: object, **kwargs: object) -> object:
        """
        Invoke a function-based handler.

        Parameters
        ----------
        func : object
            Callable resolved from the dispatch table.
        **kwargs : object
            Path parameters forwarded to the handler.

        Returns
        -------
        object
            Value returned by the handler.
        """
        return func(**kwargs)

    async def call(
        self,
        instance: object,
        method: str,
        **kwargs: object,
    ) -> object:
        """
        Invoke a controller action.

        Parameters
        ----------
        instance : object
            Controller instance built by the container.
        method : str
            Action name to invoke.
        **kwargs : object
            Path parameters forwarded to the action.

        Returns
        -------
        object
            Value returned by the action.
        """
        return getattr(instance, method)(**kwargs)


class _StubRsgiHeaders:
    """Header container mimicking the Granian RSGI header map."""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, list[str]]) -> None:
        """
        Store the header map.

        Parameters
        ----------
        data : dict[str, list[str]]
            Header names mapped to their values.
        """
        self._data = data

    def __iter__(self) -> object:
        """
        Iterate over the header names.

        Returns
        -------
        object
            Iterator over the header names.
        """
        return iter(self._data)

    def get_all(self, key: str) -> list[str]:
        """
        Return every value stored for one header.

        Parameters
        ----------
        key : str
            Header name.

        Returns
        -------
        list[str]
            Values recorded for the header.
        """
        return self._data[key]


class _StubRsgiScope:
    """Granian RSGI scope double exposing the fields the adapter reads."""

    __slots__ = (
        "authority",
        "client",
        "headers",
        "http_version",
        "method",
        "path",
        "proto",
        "query_string",
        "rsgi_version",
        "scheme",
        "server",
    )

    def __init__(self, path: str, method: str = "GET") -> None:
        """
        Build a minimal but complete RSGI scope.

        Parameters
        ----------
        path : str
            Requested path.
        method : str, optional
            HTTP method of the request.
        """
        self.proto = "http"
        self.http_version = "1.1"
        self.rsgi_version = "1.0"
        self.server = "127.0.0.1:8000"
        self.client = "127.0.0.1:51234"
        self.scheme = "http"
        self.method = method
        self.path = path
        self.query_string = ""
        self.authority = "orionis.test"
        self.headers = _StubRsgiHeaders({"host": ["orionis.test"]})


class _StubRsgiProtocol:
    """RSGI protocol double yielding an empty request body."""

    __slots__ = ()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """
        Yield no body chunk at all.

        Returns
        -------
        AsyncIterator[bytes]
            Empty asynchronous iterator.
        """
        return
        yield b""


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


def make_route(  # noqa: PLR0913
    path: str,
    method: str = "GET",
    *,
    kind: str = "api",
    function: str | None = None,
    controller: str | None = None,
    middlewares: tuple = (),
) -> CompiledRoute:
    """
    Build a compiled route pointing at a handler of this module.

    Parameters
    ----------
    path : str
        Route path.
    method : str, optional
        HTTP method served by the route.
    kind : str, optional
        Route group, either ``'web'`` or ``'api'``.
    function : str | None, optional
        Name of the module-level handler function.
    controller : str | None, optional
        Name of the controller class handling the route.
    middlewares : tuple, optional
        Route middleware classes.

    Returns
    -------
    CompiledRoute
        Route ready to be indexed by the resolver.
    """
    if function is not None:
        route_type = RouteType.FUNCTION
        action: dict[str, str] = {"module": _MODULE, "function": function}
    else:
        route_type = RouteType.CONTROLLER
        action = {"module": _MODULE, "class": controller, "method": "show"}

    return CompiledRoute(
        path=path,
        method=method,
        type=route_type,
        action=action,
        name=None,
        regex=None,
        segment_count=path.count("/"),
        kind=kind,
        compiled_middlewares=middlewares,
    )


def make_routes() -> dict[str, dict]:
    """
    Build the compiled route tables used across the kernel tests.

    Returns
    -------
    dict[str, dict]
        Route tables grouped by HTTP method.
    """
    static: dict[str, CompiledRoute] = {
        "/web": make_route("/web", kind="web", function="web_handler"),
        "/api": make_route("/api", function="api_handler"),
        "/dict": make_route("/dict", function="dict_handler"),
        "/struct": make_route("/struct", function="struct_handler"),
        "/invalid": make_route("/invalid", function="invalid_handler"),
        "/boom": make_route("/boom", function="failing_handler"),
        "/controller": make_route("/controller", controller="_Controller"),
        "/guarded": make_route(
            "/guarded",
            function="api_handler",
            middlewares=(_RecordingMiddleware,),
        ),
        "/also-guarded": make_route(
            "/also-guarded",
            function="api_handler",
            middlewares=(_RecordingMiddleware,),
        ),
        "/web-invalid": make_route(
            "/web-invalid",
            kind="web",
            function="validation_handler",
        ),
        "/api-invalid": make_route("/api-invalid", function="validation_handler"),
    }
    return {
        "GET": {"static": static, "dynamic": []},
        "QUERY": {
            "static": {"/api": make_route("/api", "QUERY", function="api_handler")},
            "dynamic": [],
        },
    }


def make_http_config(
    *,
    csrf_enabled: bool = False,
    rate_limit: dict[str, object] | None = None,
) -> dict[str, dict]:
    """
    Build the HTTP configuration section served to the kernel.

    Parameters
    ----------
    csrf_enabled : bool, optional
        Whether CSRF protection must be active.
    rate_limit : dict[str, object] | None, optional
        Rate-limit settings; defaults to the disabled limiter.

    Returns
    -------
    dict[str, dict]
        Configuration consumed by the global middleware stack.
    """
    return {
        "proxies": {},
        "security": {},
        "cors": {
            "allow_origins": ["*"],
            "allow_methods": ["GET", "POST"],
            "allow_headers": ["*"],
        },
        "rate_limit": rate_limit if rate_limit is not None else {},
        "csrf": {"enabled": csrf_enabled},
    }


async def boot_kernel(  # noqa: PLR0913
    *,
    routes: dict[str, dict] | None = None,
    fallback: tuple | None = None,
    debug: bool = False,
    maintenance: bool = False,
    csrf_enabled: bool = False,
    rate_limit: dict[str, object] | None = None,
) -> tuple[KernelHTTP, _StubApp, _StubDefaultResponses, _StubCatch]:
    """
    Build and boot a kernel wired to fully controlled collaborators.

    Parameters
    ----------
    routes : dict[str, dict] | None, optional
        Compiled route tables; defaults to the shared fixture.
    fallback : tuple | None, optional
        Fallback handler descriptor.
    debug : bool, optional
        Whether the application runs in debug mode.
    maintenance : bool, optional
        Whether the application is under maintenance.
    csrf_enabled : bool, optional
        Whether CSRF protection must be active.
    rate_limit : dict[str, object] | None, optional
        Rate-limit settings applied to the global middleware stack.

    Returns
    -------
    tuple[KernelHTTP, _StubApp, _StubDefaultResponses, _StubCatch]
        Booted kernel and the doubles it was wired with.
    """
    responses = _StubDefaultResponses()
    catch = _StubCatch()
    builds: dict[type, object] = {
        RouteLoader: _StubRouteLoader(
            routes if routes is not None else make_routes(),
            fallback,
        ),
        DefaultResponses: responses,
        StartSessionMiddleware: _SessionMiddlewareDouble(),
        RSGIResponseAdapter: _StubResponseAdapter(),
        ASGIResponseAdapter: _StubResponseAdapter(),
        HTTPRequestPrinter: _StubRequestPrinter(),
    }
    app = _StubApp(
        builds,
        {
            "http": make_http_config(
                csrf_enabled=csrf_enabled,
                rate_limit=rate_limit,
            ),
        },
        debug=debug,
        maintenance=maintenance,
    )
    kernel = KernelHTTP(app=app, catch=catch)
    await kernel.boot()
    return kernel, app, responses, catch


def make_asgi_scope(
    path: str,
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    """
    Build a minimal ASGI scope for the kernel entry point.

    Parameters
    ----------
    path : str
        Requested path.
    method : str, optional
        HTTP method of the request.
    headers : list[tuple[bytes, bytes]] | None, optional
        Raw header pairs.

    Returns
    -------
    dict[str, Any]
        Scope accepted by the ASGI transport adapter.
    """
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": list(headers or [(b"host", b"orionis.test")]),
        "scheme": "http",
        "server": ("orionis.test", 80),
        "client": ("127.0.0.1", 51234),
        "http_version": "1.1",
    }


async def receive_empty() -> dict[str, Any]:
    """
    Return an empty ASGI request message.

    Returns
    -------
    dict[str, Any]
        Message declaring an empty, complete body.
    """
    return {"type": "http.request", "body": b"", "more_body": False}


async def send_noop(_message: object) -> None:
    """
    Discard an ASGI response message.

    Parameters
    ----------
    _message : object
        Message produced by the response adapter.
    """
    return


async def dispatch(
    kernel: KernelHTTP,
    path: str,
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Response:
    """
    Run one ASGI request through the kernel end to end.

    Parameters
    ----------
    kernel : KernelHTTP
        Booted kernel under test.
    path : str
        Requested path.
    method : str, optional
        HTTP method of the request.
    headers : list[tuple[bytes, bytes]] | None, optional
        Raw header pairs.

    Returns
    -------
    Response
        Response handed to the transport adapter.
    """
    return await kernel.handleASGI(
        make_asgi_scope(path, method, headers),
        receive_empty,
        send_noop,
    )


def make_request_double(path: str) -> Request:
    """
    Build a lightweight request for middleware pipeline tests.

    Parameters
    ----------
    path : str
        Requested path exposed by the request.

    Returns
    -------
    Request
        Request backed by a minimal ASGI scope.
    """
    return Request(
        interface=Interface.ASGI,
        adapter=ASGITransportAdapter(make_asgi_scope(path)),
        body_stream=BodyStream(
            interface=Interface.ASGI,
            receive_or_protocol=receive_empty,
        ),
    )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class TestMiddlewarePipeline(TestCase):

    async def testInvokesTheTerminalWithoutMiddleware(self) -> None:
        """
        Call the terminal handler when the stack is empty.

        Validates the fast path taken by routes without middleware.
        """
        expected = Response(content="terminal")

        async def terminal() -> Response:
            return expected

        pipeline = kernel_module._MiddlewarePipeline((), None, terminal)
        self.assertIs(await pipeline(), expected)

    async def testRunsEveryLayerInOrder(self) -> None:
        """
        Walk every middleware layer before reaching the terminal.

        Validates the ordering guarantee route stacks rely on.
        """
        _RecordingMiddleware.calls = [] # NOSONAR
        request = make_request_double("/x")

        async def terminal() -> Response:
            return Response(content="terminal")

        pipeline = kernel_module._MiddlewarePipeline(
            (_RecordingMiddleware(), _RecordingMiddleware()),
            request,
            terminal,
        )
        response = await pipeline()
        self.assertEqual(len(_RecordingMiddleware.calls), 2)
        self.assertEqual(response.getHeader("x-route-middleware"), ["1"])

    async def testRejectsADoubleAdvanceFromTheSameLayer(self) -> None:
        """
        Reject a middleware calling ``next()`` twice.

        Validates the guard that prevents a handler from running twice
        for a single request.
        """

        async def terminal() -> Response:
            return Response(content="terminal")

        pipeline = kernel_module._MiddlewarePipeline(
            (_DoubleNextMiddleware(), _RecordingMiddleware()),
            make_request_double("/x"),
            terminal,
        )
        with self.assertRaises(RuntimeError):
            await pipeline()


class TestKernelBoot(TestCase):

    async def testBootWiresEveryCollaborator(self) -> None:
        """
        Resolve every collaborator exactly once during boot.

        Validates that the request hot path never touches the container.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        self.assertTrue(kernel._KernelHTTP__boot)

    async def testBootIsIdempotent(self) -> None:
        """
        Ignore a second boot request.

        Validates that re-entering ``boot()`` cannot duplicate the
        middleware stacks.
        """
        kernel, app, _responses, _catch = await boot_kernel()
        printer = app.builds[HTTPRequestPrinter]
        printer.timers = 0
        await kernel.boot()
        self.assertEqual(printer.timers, 0)

    async def testBuildsTheOrderedWebPipeline(self) -> None:
        """
        Install the session middleware before the CSRF middleware.

        Validates the ordering the flash bag depends on.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        stack = kernel._KernelHTTP__web_middleware
        self.assertIsInstance(stack[0], _SessionMiddlewareDouble)
        self.assertIsInstance(stack[1], CSRFTokenMiddleware)

    async def testPreloadsFunctionAndControllerHandlers(self) -> None:
        """
        Resolve every handler into an identity-keyed dispatch table.

        Validates that no module import happens while serving a request.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        self.assertIn(web_handler, kernel._KernelHTTP__fn_dispatch.values())
        self.assertIn(
            (_Controller, "show"),
            kernel._KernelHTTP__cls_dispatch.values(),
        )

    async def testSharesMiddlewareInstancesAcrossIdenticalStacks(self) -> None:
        """
        Build one middleware tuple per distinct route stack.

        Validates the cache that keeps boot time and memory bounded.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        cache = kernel._KernelHTTP__middleware_cache
        self.assertEqual(len(cache), 1)
        self.assertEqual(len(next(iter(cache.values()))), 1)

    async def testKeepsTheRegisteredFallback(self) -> None:
        """
        Cache the fallback handler resolved at boot time.

        Validates that unmatched routes can be served without a lookup.
        """
        fallback = (_FallbackController, "handle")
        kernel, _app, _responses, _catch = await boot_kernel(fallback=fallback)
        self.assertEqual(kernel._KernelHTTP__fallback, fallback)

    async def testTreatsAnEmptyFallbackPairAsAbsent(self) -> None:
        """
        Ignore the placeholder fallback pair produced by the loader.

        Validates that ``(None, None)`` never reaches the dispatcher.
        """
        kernel, _app, _responses, _catch = await boot_kernel(
            fallback=(None, None),
        )
        self.assertIsNone(kernel._KernelHTTP__fallback)

    async def testReportsNoFallbackWhenNoneIsRegistered(self) -> None:
        """
        Leave the fallback unset when the loader registers none.

        Validates the default configuration of a fresh application.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        self.assertIsNone(kernel._KernelHTTP__fallback)

    async def testEnablesTheRequestPrinterInDebugMode(self) -> None:
        """
        Activate the debug request printer only in debug mode.

        Validates that production requests skip the timer and the log
        call entirely.
        """
        _kernel, app, _responses, _catch = await boot_kernel(debug=True)
        self.assertTrue(app.builds[HTTPRequestPrinter].enabled)

    async def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep the kernel free of a per-instance dictionary.

        Validates the slot layout declared by the class.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        self.assertFalse(hasattr(kernel, "__dict__"))


class TestKernelDispatch(TestCase):

    async def testServesAnApiRoute(self) -> None:
        """
        Dispatch an API route straight to its handler.

        Validates the fast path taken by routes without middleware.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/api")
        self.assertEqual(response.getBody(), b"api")

    async def testServesAWebRouteThroughTheWebPipeline(self) -> None:
        """
        Route a web request through the session and CSRF layers.

        Validates that the flash bag and CSRF token are always available
        to web handlers.
        """
        _SessionMiddlewareDouble.calls = [] # NOSONAR
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/web")
        self.assertEqual(response.getBody(), b"web")
        self.assertEqual(_SessionMiddlewareDouble.calls, ["/web"])

    async def testServesAControllerAction(self) -> None:
        """
        Dispatch a class-based route to its controller action.

        Validates the second dispatch table built at boot time.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/controller")
        self.assertEqual(response.getBody(), b"controller")

    async def testCoercesAMappingIntoJson(self) -> None:
        """
        Serialise a mapping returned by a handler.

        Validates the convenience relied upon by simple API endpoints.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/dict")
        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.getBody(), b'{"answer":42}')

    async def testCoercesAStructIntoJson(self) -> None:
        """
        Serialise a structured payload returned by a handler.

        Validates support for schema objects as handler return values.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/struct")
        self.assertEqual(response.getBody(), b'{"name":"orionis"}')

    async def testRejectsAHandlerThatReturnsNothing(self) -> None:
        """
        Report a handler that does not return a response.

        Validates the diagnostic surfaced through the failure handler.
        """
        kernel, _app, _responses, catch = await boot_kernel()
        await dispatch(kernel, "/invalid")
        self.assertIsInstance(catch.handled[0], TypeError)

    async def testRunsRouteMiddleware(self) -> None:
        """
        Execute the middleware stack attached to a route.

        Validates that the pre-built instances are actually used.
        """
        _RecordingMiddleware.calls = [] # NOSONAR
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/guarded")
        self.assertEqual(_RecordingMiddleware.calls, ["/guarded"])
        self.assertEqual(response.getHeader("x-route-middleware"), ["1"])

    async def testBuildsAMissingMiddlewareStackOnDemand(self) -> None:
        """
        Build a route middleware stack absent from the boot-time cache.

        Validates the recovery path for stacks registered after boot.
        """
        _RecordingMiddleware.calls = [] # NOSONAR
        kernel, _app, _responses, _catch = await boot_kernel()
        kernel._KernelHTTP__middleware_cache.clear()
        response = await dispatch(kernel, "/guarded")
        self.assertEqual(response.getStatusCode(), 200)
        self.assertEqual(len(kernel._KernelHTTP__middleware_cache), 1)

    async def testRegistersTheRequestInTheScope(self) -> None:
        """
        Publish the request and the kernel context in the active scope.

        Validates the per-request bindings resolved by the container.
        """
        kernel, app, _responses, _catch = await boot_kernel()
        await dispatch(kernel, "/api")
        scope = app.scopes[-1]
        self.assertEqual(scope.tags["kernel"], KernelContext.HTTP)
        self.assertIsInstance(scope.entries[Request], Request)


class TestKernelGlobalMiddleware(TestCase):

    async def testRejectsEveryRequestUnderMaintenance(self) -> None:
        """
        Answer with ``503`` while the application is under maintenance.

        Validates that no handler runs during a deployment.
        """
        kernel, _app, responses, _catch = await boot_kernel(maintenance=True)
        response = await dispatch(kernel, "/api")
        self.assertEqual(response.getStatusCode(), 503)
        self.assertEqual(responses.calls[0][0], 503)

    async def testRejectsDuplicateHostHeaders(self) -> None:
        """
        Answer with ``400`` when two host headers are supplied.

        Validates the request-smuggling guard of the security layer.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(
            kernel,
            "/api",
            headers=[(b"host", b"a.test"), (b"host", b"b.test")],
        )
        self.assertEqual(response.getStatusCode(), 400)

    async def testAnswersCorsPreflightRequests(self) -> None:
        """
        Answer a CORS preflight before reaching the router.

        Validates that browsers receive the negotiated headers without
        running a handler.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(
            kernel,
            "/api",
            "OPTIONS",
            headers=[
                (b"host", b"orionis.test"),
                (b"origin", b"http://front.test"),
                (b"access-control-request-method", b"GET"),
            ],
        )
        self.assertEqual(response.getStatusCode(), 204)
        self.assertTrue(response.hasHeader("access-control-allow-methods"))


class TestKernelOptionsRequests(TestCase):

    async def testAdvertisesTheAllowedMethods(self) -> None:
        """
        Answer an ``OPTIONS`` request with the allowed methods.

        Validates the introspection endpoint offered for every path.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/web", "OPTIONS")
        self.assertEqual(response.getStatusCode(), 200)
        self.assertIn("GET", response.getHeader("Allow")[0])

    async def testAdvertisesTheQueryPayloadTypes(self) -> None:
        """
        Advertise the accepted payload types for ``QUERY`` routes.

        Validates the extra header emitted only when the path also
        answers the ``QUERY`` method.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/api", "OPTIONS")
        self.assertTrue(response.hasHeader("Accept-Query"))


class TestKernelValidationFailures(TestCase):

    async def testWebRoutesRedirectBackWithTheErrors(self) -> None:
        """
        Redirect a browser back when validation fails on a web route.

        Validates that the redirect is produced inside the session
        middleware so the flash bag survives.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/web-invalid")
        self.assertEqual(response.getStatusCode(), 302)

    async def testApiRoutesReportTheFieldErrors(self) -> None:
        """
        Answer with ``422`` when validation fails on an API route.

        Validates the structured payload returned to JSON clients.
        """
        kernel, _app, responses, _catch = await boot_kernel()
        response = await dispatch(kernel, "/api-invalid")
        self.assertEqual(response.getStatusCode(), 422)
        self.assertTrue(responses.calls[-1][2])


class TestKernelFailureHandling(TestCase):

    async def testDelegatesUnhandledErrorsToTheFailureHandler(self) -> None:
        """
        Forward an unexpected exception to the failure handler.

        Validates that a broken handler never leaks a traceback to the
        transport.
        """
        kernel, _app, _responses, catch = await boot_kernel()
        response = await dispatch(kernel, "/boom")
        self.assertEqual(response.getStatusCode(), 500)
        self.assertIsInstance(catch.handled[0], RuntimeError)

    async def testDelegatesUnmatchedRoutesToTheFailureHandler(self) -> None:
        """
        Forward an unmatched path to the failure handler.

        Validates the behaviour of an application without a fallback.
        """
        kernel, _app, _responses, catch = await boot_kernel()
        await dispatch(kernel, "/nowhere")
        self.assertIsInstance(catch.handled[0], RouteNotFound)

    async def testServesTheControllerFallback(self) -> None:
        """
        Serve an unmatched path through the class-based fallback.

        Validates the custom 404 page registered by applications.
        """
        kernel, _app, _responses, _catch = await boot_kernel(
            fallback=(_FallbackController, "handle"),
        )
        response = await dispatch(kernel, "/nowhere")
        self.assertEqual(response.getBody(), b"fallback-controller")

    async def testServesTheCallableFallback(self) -> None:
        """
        Serve an unmatched path through a callable fallback.

        Validates the closure-based registration form.
        """
        kernel, _app, _responses, _catch = await boot_kernel(
            fallback=(None, fallback_function),
        )
        response = await dispatch(kernel, "/nowhere")
        self.assertEqual(response.getBody(), b"fallback-function")

    async def testRejectsAFallbackThatReturnsNothing(self) -> None:
        """
        Report a fallback that does not return a response.

        Validates that the developer error surfaces instead of being
        answered with a malformed response.
        """
        kernel, _app, _responses, _catch = await boot_kernel(
            fallback=(_BrokenFallbackController, "handle"),
        )
        with self.assertRaises(TypeError):
            await dispatch(kernel, "/nowhere")


class TestKernelRequestLogging(TestCase):

    async def testLogsRequestsInDebugMode(self) -> None:
        """
        Log every request while the application runs in debug mode.

        Validates the timer and the printer are both driven by the same
        cached flag.
        """
        kernel, app, _responses, _catch = await boot_kernel(debug=True)
        response = await dispatch(kernel, "/api")
        printer = app.builds[HTTPRequestPrinter]
        self.assertEqual(printer.timers, 1)
        self.assertEqual(printer.printed, [response])

    async def testSkipsLoggingOutsideDebugMode(self) -> None:
        """
        Skip request logging when debug mode is disabled.

        Validates the optimisation applied to production traffic.
        """
        kernel, app, _responses, _catch = await boot_kernel()
        await dispatch(kernel, "/api")
        printer = app.builds[HTTPRequestPrinter]
        self.assertEqual(printer.timers, 0)
        self.assertEqual(printer.printed, [])


class TestKernelRateLimiting(TestCase):

    async def testSkipsTheLimiterWhenDisabled(self) -> None:
        """
        Bypass the limiter entirely when it is turned off.

        Validates the cached flag that keeps the disabled configuration
        free of asynchronous overhead.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        self.assertFalse(kernel._KernelHTTP__rate_limit_enabled)
        self.assertEqual((await dispatch(kernel, "/api")).getStatusCode(), 200)

    async def testAllowsRequestsWithinTheQuota(self) -> None:
        """
        Serve the request when the client is within its quota.

        Validates the branch where the limiter defers to the router.
        """
        kernel, _app, _responses, _catch = await boot_kernel(
            rate_limit={
                "rate_limit_enabled": True,
                "rate_limit_requests": 5,
                "rate_limit_window_seconds": 60,
            },
        )
        self.assertEqual((await dispatch(kernel, "/api")).getStatusCode(), 200)

    async def testRejectsRequestsOverTheQuota(self) -> None:
        """
        Answer with ``429`` once the quota is exhausted.

        Validates that the limiter short-circuits the router.
        """
        kernel, _app, _responses, _catch = await boot_kernel(
            rate_limit={
                "rate_limit_enabled": True,
                "rate_limit_requests": 1,
                "rate_limit_window_seconds": 60,
            },
        )
        await dispatch(kernel, "/api")
        self.assertEqual((await dispatch(kernel, "/api")).getStatusCode(), 429)


class TestKernelRsgiEntryPoint(TestCase):

    async def testServesAnRsgiRequest(self) -> None:
        """
        Handle a Granian RSGI request end to end.

        Validates the transport-specific entry point and its response
        adapter.
        """
        kernel, app, _responses, _catch = await boot_kernel()
        response = await kernel.handleRSGI(
            _StubRsgiScope("/api"),
            _StubRsgiProtocol(),
        )
        self.assertEqual(response.getBody(), b"api")
        self.assertEqual(app.builds[RSGIResponseAdapter].sent, [response])

    async def testLogsRsgiRequestsInDebugMode(self) -> None:
        """
        Log RSGI requests while the application runs in debug mode.

        Validates parity between the two transport entry points.
        """
        kernel, app, _responses, _catch = await boot_kernel(debug=True)
        await kernel.handleRSGI(_StubRsgiScope("/api"), _StubRsgiProtocol())
        self.assertEqual(len(app.builds[HTTPRequestPrinter].printed), 1)
