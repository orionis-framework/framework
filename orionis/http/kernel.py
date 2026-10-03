import importlib
from contextlib import suppress
from operator import attrgetter
from threading import BoundedSemaphore
from typing import TYPE_CHECKING
import msgspec
from orionis.auth.middleware.resolve_identity import (
    ResolveSessionIdentityMiddleware,
    ResolveTokenIdentityMiddleware,
)
from orionis.console.output.http_request import HTTPRequestPrinter
from orionis.container.entities.invocation import callable_plan, warm_controller_plan
from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.foundation.config.http.entitites.body import HTTPBodyLimits
from orionis.foundation.config.http.entitites.websocket import HTTPWebSocket
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.request.rsgi import RSGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.contracts.kernel import IKernelHTTP
from orionis.http.default.responses import DefaultResponses
from orionis.http.enums.interfaces import Interface
from orionis.http.enums.status import HTTPStatus
from orionis.http.layer.shared.cors import CORSMiddleware
from orionis.http.layer.shared.maintenance import UnderMaintenanceMiddleware
from orionis.http.layer.shared.proxies import ProxiesMiddleware
from orionis.http.layer.shared.rate_limit import RateLimitMiddleware
from orionis.http.layer.shared.security import SecurityMiddleware
from orionis.http.layer.web.csrf_token import CSRFTokenMiddleware
from orionis.http.layer.web.start_session import StartSessionMiddleware
from orionis.http.payload.body import PayloadTooLargeException
from orionis.http.request import Request
from orionis.http.responses import JSONResponse, Response
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.loader import RouteLoader
from orionis.http.routes.route_resolver import RouteResolver
from orionis.http.validation import validation_response
from orionis.http.websocket import WebSocket, WebSocketDisconnected
from orionis.schemas.exceptions.validation import ValidationException
from orionis.support.facades.view import View

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from granian.rsgi import HTTPProtocol, Scope, WebsocketProtocol
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.routes.contracts.loader import IRouteLoader
    from orionis.http.routes.entities.resolved_route import ResolvedRoute

# Handler return types that are serialized as JSON.
_JSON_RESPONSE_TYPES: tuple[type, ...] = (dict, msgspec.Struct)

# Kernel context identifier reused across all request scopes.
_KERNEL_CONTEXT: KernelContext = KernelContext.HTTP

class _MiddlewareNext[T]:
    """Hold one request-local continuation that can be consumed only once."""

    __slots__ = ("_args", "_called", "_terminal")

    def __init__(self, terminal: Callable, args: tuple) -> None:
        """
        Bind a continuation to its fixed arguments.

        Parameters
        ----------
        terminal : Callable
            Asynchronous next middleware or handler.
        args : tuple
            Arguments supplied when advancing the pipeline.

        Returns
        -------
        None
            The continuation is ready for one invocation.
        """
        self._terminal = terminal
        self._args = args
        self._called = False

    async def __call__(self) -> T:
        """
        Advance once, including when concurrent tasks call the continuation.

        Returns
        -------
        Response
            Response returned by the next middleware or handler.

        Raises
        ------
        RuntimeError
            If the middleware already consumed this continuation.
        """
        if self._called:
            error_msg = "next() has already been called in this middleware layer."
            raise RuntimeError(error_msg)
        self._called = True
        return await self._terminal(*self._args)

class _MiddlewarePipeline[T]:
    """
    Middleware pipeline with request-local execution state.

    A single instance encapsulates the execution state for one middleware stack
    invocation. Each layer receives a fixed continuation so concurrent
    invocations cannot change the depth observed by another middleware.
    """

    __slots__ = (
        "_called_mask",
        "_instances",
        "_n",
        "_request",
        "_terminal",
        "_terminal_args",
    )

    def __init__(
        self,
        instances: tuple,
        request: Request | WebSocket,
        terminal: Callable[..., Awaitable[T]],
        terminal_args: tuple = (),
    ) -> None:
        """
        Store the middleware stack and terminal callable for one request.

        Parameters
        ----------
        instances : tuple
            Ordered tuple of pre-built middleware instances.
        request : Request
            Incoming HTTP request forwarded to each layer.
        terminal : Callable[..., Awaitable[Response]]
            Async callable invoked after all middleware layers have run.
        terminal_args : tuple, optional
            Positional arguments forwarded to the terminal callable.

        Returns
        -------
        None
        """
        self._instances = instances
        self._request = request
        self._terminal = terminal
        self._terminal_args = terminal_args
        self._n = len(instances)
        self._called_mask = 0

    async def __call__(self) -> T:
        """
        Advance to the next middleware layer or invoke the terminal handler.

        Returns
        -------
        Response
            HTTP response produced by the next layer or the terminal.

        Raises
        ------
        RuntimeError
            When ``next()`` is invoked more than once in the same layer.
        """
        return await self.__advance(0)

    async def __advance(self, depth: int) -> T:
        """
        Invoke the layer at a fixed depth with its own continuation.

        Parameters
        ----------
        depth : int
            Position of the middleware or terminal to execute.

        Returns
        -------
        Response
            Response returned by this middleware and its descendants.
        """
        bit = 1 << depth
        # Guard against double invocation of next() from the same layer.
        if self._called_mask & bit:
            error_msg = "next() has already been called in this middleware layer."
            raise RuntimeError(error_msg)
        self._called_mask |= bit
        # The terminal also consumes its continuation exactly once.
        if depth >= self._n:
            return await self._terminal(*self._terminal_args)
        continuation = _MiddlewareNext(self.__advance, (depth + 1,))
        return await self._instances[depth].handle(self._request, continuation)

class KernelHTTP(IKernelHTTP):

    # ruff: noqa:TC001 - For Dependency injection

    __slots__ = (
        "__api_middleware",
        "__app",
        "__asgi_adapter",
        "__body_limits",
        "__boot",
        "__catch",
        "__cls_dispatch",
        "__cors",
        "__default_responses",
        "__fallback",
        "__fn_dispatch",
        "__health_path",
        "__middleware_cache",
        "__printer_enabled",
        "__proxies",
        "__rate_limit",
        "__rate_limit_enabled",
        "__request_printer",
        "__request_slots",
        "__routes",
        "__rsgi_adapter",
        "__security",
        "__under_maintenance",
        "__view_dispatch",
        "__web_middleware",
        "__websocket_config",
        "__websocket_slots",
    )

    def __init__(
        self,
        app: IApplication,
        catch: ICatch,
    ) -> None:
        """
        Initialize the HTTP kernel with application and failure handler.

        Parameters
        ----------
        app : IApplication
            Application instance providing configuration and DI container.
        catch : ICatch
            Failure handler used to format unhandled exceptions.

        Returns
        -------
        None
        """
        self.__app = app
        self.__boot: bool = False
        self.__catch: ICatch = catch
        self.__body_limits = HTTPBodyLimits()
        self.__request_slots = BoundedSemaphore(
            self.__body_limits.max_concurrent_requests,
        )
        self.__websocket_config = HTTPWebSocket()
        self.__websocket_slots = BoundedSemaphore(
            self.__websocket_config.max_connections,
        )
        # Associate each route middleware stack with its instances.
        self.__middleware_cache: dict[tuple, tuple] = {}

    async def boot(self) -> None:
        """
        Boot the HTTP kernel by initializing all core components.

        Returns
        -------
        None
        """
        # Prevent redundant initialization on repeated calls.
        if self.__boot:
            return

        # Build the route resolver from the loaded route definitions.
        self.__routeResolve(
            route_loader=await self.__app.build(RouteLoader),
        )

        # Eagerly import all handler modules and build int-keyed dispatch tables.
        await self.__preloadHandlers()

        # Pre-build middleware instance tuples for every route stack.
        await self.__preloadMiddleware()

        # Build the default response factory for common HTTP error responses.
        self.__default_responses: IDefaultResponses = await self.__app.build(
            DefaultResponses,
        )

        # Instantiate global middleware from the application HTTP configuration.
        self.__defaultMiddleware(
            http_config=self.__app.config("http"),
            default_responses=self.__default_responses,
            under_maintenance=self.__app.underMaintenance(),
        )
        self.__health_path = self.__app.routeHealthCheck.rstrip("/")

        # Resolve web identities only after session restoration and CSRF checks.
        self.__web_middleware: tuple = (
            await self.__app.build(StartSessionMiddleware),
            CSRFTokenMiddleware(config=self.__app.config("http").get("csrf", {})),
            await self.__app.build(ResolveSessionIdentityMiddleware),
        )
        # API identity resolution uses Bearer credentials without starting a session.
        self.__api_middleware: tuple = (
            await self.__app.build(ResolveTokenIdentityMiddleware),
        )

        # Protocol-level response adapters for RSGI and ASGI transports.
        self.__rsgi_adapter = await self.__app.build(RSGIResponseAdapter)
        self.__asgi_adapter = await self.__app.build(ASGIResponseAdapter)

        # Request logger; only active when the application runs in debug mode.
        self.__request_printer = await self.__app.build(HTTPRequestPrinter)
        self.__request_printer.setEnabled(enabled=self.__app.isDebug())
        # Record whether requests should be timed and logged.
        self.__printer_enabled: bool = self.__app.isDebug()

        # Resolve the registered fallback handler.
        _raw_fallback = self.__routes.fallback()
        self.__fallback: tuple | None = (
            _raw_fallback
            if (_raw_fallback is not None and _raw_fallback != (None, None))
            else None
        )

        self.__boot = True

    def __routeResolve(
        self,
        route_loader: IRouteLoader,
    ) -> None:
        """
        Initialize route resolver with loaded routes.

        Build a route resolver instance configured with routes loaded
        from the provided route loader and cache settings.

        Parameters
        ----------
        route_loader : IRouteLoader
            Route loader instance to discover and load routes.

        Returns
        -------
        None
        """
        # Build the resolver with compiled routes and a fixed hot-cache budget.
        self.__routes = RouteResolver(
            routes=route_loader.load(),
            fallback=route_loader.fallback,
            hot_cache_size=512,
        )

    async def __preloadHandlers(self) -> None:
        """
        Import route handlers and prepare their dependency metadata at boot time.

        Populates two int-keyed dispatch tables using route object identity,
        eliminating per-request module imports, attribute lookups, and tuple
        key construction from the handler invocation hot path. View routes are
        stored in a third table holding only their template name. Ordinary
        constructor and action plans are prepared without resolving services
        or creating controller instances. Custom descriptors remain lazy.

        Returns
        -------
        None
        """
        fn_dispatch: dict[int, object] = {}
        cls_dispatch: dict[int, tuple[type, str]] = {}
        view_dispatch: dict[int, str] = {}
        module_cache: dict[str, object] = {}

        # Walk every registered route once and store fully resolved callables.
        for route in self.__routes.allRoutes():
            action = route.action
            route_id = id(route)

            # View routes have no Python handler; bind the template directly.
            if route.type is RouteType.VIEW:
                view_dispatch[route_id] = action["view"]
                continue

            module_name = action["module"]
            module = module_cache.get(module_name)
            if module is None:
                module = importlib.import_module(module_name)
                module_cache[module_name] = module

            if route.type is RouteType.FUNCTION:
                function = attrgetter(action["function"])(module)
                callable_plan(function)
                fn_dispatch[route_id] = function
            else:
                controller = attrgetter(action["class"])(module)
                method = action["method"]
                warm_controller_plan(controller, method)
                cls_dispatch[route_id] = (controller, method)

        self.__fn_dispatch: dict[int, object] = fn_dispatch
        self.__cls_dispatch: dict[int, tuple[type, str]] = cls_dispatch
        self.__view_dispatch: dict[int, str] = view_dispatch

    def __defaultMiddleware(
        self,
        http_config: dict,
        default_responses: IDefaultResponses,
        *,
        under_maintenance: bool = False,
    ) -> None:
        """
        Initialize default HTTP middleware stack.

        Configure and instantiate the default middleware chain including
        proxies, security, CORS, and rate limiting middleware.

        Parameters
        ----------
        http_config : dict
            HTTP configuration dictionary with middleware settings.
        default_responses : IDefaultResponses
            Default response handler for middleware rejections.

        Returns
        -------
        None
        """
        limits = http_config.get("body_limits", {})
        websocket = http_config.get("websocket", {})
        self.__websocket_config = (
            websocket if isinstance(websocket, HTTPWebSocket)
            else HTTPWebSocket(**websocket)
        )
        self.__websocket_slots = BoundedSemaphore(
            self.__websocket_config.max_connections,
        )
        self.__body_limits = (
            limits if isinstance(limits, HTTPBodyLimits) else HTTPBodyLimits(**limits)
        )
        self.__request_slots = BoundedSemaphore(
            self.__body_limits.max_concurrent_requests,
        )
        self.__proxies = ProxiesMiddleware(
            config=http_config.get("proxies"),
        )
        self.__security = SecurityMiddleware(
            config=http_config.get("security"),
            default_responses=default_responses,
        )
        self.__cors = CORSMiddleware(
            config=http_config.get("cors"),
        )
        self.__rate_limit = RateLimitMiddleware(
            config=http_config.get("rate_limit"),
            default_responses=default_responses,
        )
        self.__under_maintenance = UnderMaintenanceMiddleware(
            under_maintenance=under_maintenance,
            default_responses=default_responses,
        )
        # Record whether rate limiting is active.
        self.__rate_limit_enabled = self.__rate_limit.isEnabled()
        if (
            self.__rate_limit_enabled
            and http_config["rate_limit"].get("rate_limit_store", "memory") == "redis"
        ):
            self.__app.on(
                Lifespan.SHUTDOWN, self.__rate_limit.close, runtime=Runtime.HTTP,
            )

    async def __rsgiResponse(
        self,
        adapter: RSGITransportAdapter,
        response: Response,
        protocol: HTTPProtocol,
    ) -> None:
        """
        Send an RSGI HTTP response through the transport adapter.

        Apply CORS post-processing headers, log request details, and send
        the response back to the client via the RSGI protocol adapter.

        Parameters
        ----------
        adapter : RSGITransportAdapter
            RSGI transport adapter with HTTP scope and client connection.
        response : Response
            HTTP response object to send to client.
        protocol : HTTPProtocol
            RSGI HTTP protocol version indicator.

        Returns
        -------
        None
        """
        self.__cors.after(adapter, response)
        # Log request details only when the debug printer is active.
        if self.__printer_enabled:
            self.__request_printer.printRequest(adapter, response)
        return await self.__rsgi_adapter.send(adapter, response, protocol)

    async def __asgiResponse(
        self,
        adapter: TransportAdapter,
        response: Response,
        receive: object,
        send: object,
    ) -> None:
        """
        Send ASGI HTTP response through transport adapter.

        Apply CORS post-processing headers, log request details, and send
        the response back to the client via ASGI protocol adapter.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport adapter encapsulating the HTTP request.
        response : Response
            HTTP response object to send to client.
        receive : object
            ASGI receive callable for reading request body.
        send : object
            ASGI send callable for sending response.

        Returns
        -------
        None
        """
        self.__cors.after(adapter, response)
        # Log request details only when the debug printer is active.
        if self.__printer_enabled:
            self.__request_printer.printRequest(adapter, response)
        return await self.__asgi_adapter.send(
            adapter, response, receive, send,
        )

    async def __globalMiddleware(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
        """
        Execute global middleware and serve packaged default-page assets.

        Process request through middleware pipeline: proxies detection,
        security validation, and CORS negotiation. Framework assets remain
        available during maintenance and after rate-limit rejections.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport adapter encapsulating the HTTP request.

        Returns
        -------
        Response | None
            HTTP response if middleware rejects request, None if request
            passes all middleware checks.
        """
        # Apply trusted-proxy IP and scheme normalization.
        adapter = self.__proxies.handle(adapter)
        # Default pages need their assets even when application access is denied.
        path = adapter.path()
        is_asset = path.startswith(DefaultResponses.ASSET_PREFIX)
        # Check shared maintenance state for application routes.
        if (
            not is_asset
            and path.rstrip("/") != self.__health_path
            and self.__app.underMaintenance()
        ):
            response = await self.__under_maintenance.handle(
                adapter,
                under_maintenance=True,
            )
            if response is not None:
                return response
        # Enforce baseline security header policies.
        response = await self.__security.handle(adapter)
        if response is not None:
            return response
        if is_asset and adapter.method() not in {"GET", "HEAD"}:
            return Response(status_code=405, headers={"Allow": "GET, HEAD"})
        # Validate origin and handle CORS preflight requests.
        response = self.__cors.before(adapter)
        if response is not None or not is_asset:
            return response
        return self.__default_responses.asset(
            path[len(DefaultResponses.ASSET_PREFIX):],
        )

    async def __preloadMiddleware(self) -> None:
        """
        Pre-build middleware instances for all routes at boot time.

        Iterate every compiled route and eagerly resolve each middleware
        class through the container. Results are stored keyed by the
        immutable stack tuple so identical stacks share the same instances.

        Returns
        -------
        None
        """
        for route in self.__routes.allRoutes():
            if route.method == "WEBSOCKET":
                continue
            stack = route.compiled_middlewares
            if stack and stack not in self.__middleware_cache:
                built = [await self.__app.build(mw_class) for mw_class in stack]
                self.__middleware_cache[stack] = tuple(built)

    async def __routeLayer(
        self,
        request: Request,
        resolved_route: ResolvedRoute,
    ) -> Response:
        """
        Establish the web or API context before running route middleware.

        Web routes restore the session, validate CSRF, and resolve the session
        identity. API routes resolve only the token identity. Both allow guests;
        access restrictions belong to the application's route middleware.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        resolved_route : ResolvedRoute
            Resolved route metadata.

        Returns
        -------
        Response
            HTTP response produced by the middleware pipeline.
        """
        if resolved_route.route.public:
            return await self.__requestLayer(request, resolved_route)
        if resolved_route.kind == "web":
            instances = self.__web_middleware
            terminal = self.__webTerminal
        else:
            instances = self.__api_middleware
            terminal = self.__requestLayer

        if not instances:
            return await terminal(request, resolved_route)
        if len(instances) == 1:
            return await instances[0].handle(
                request, _MiddlewareNext(terminal, (request, resolved_route)),
            )

        # Keep continuation state local to this request.
        pipeline = _MiddlewarePipeline(
            instances=instances,
            request=request,
            terminal=terminal,
            terminal_args=(request, resolved_route),
        )
        return await pipeline()

    async def __webTerminal(
        self,
        request: Request,
        resolved_route: ResolvedRoute,
    ) -> Response:
        """
        Run the route pipeline and translate validation failures for the web.

        Validation errors are caught here, inside the session middleware, so
        the resulting redirect still gets its flash bag persisted.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        resolved_route : ResolvedRoute
            Resolved route metadata.

        Returns
        -------
        Response
            Handler response, or a redirect back carrying the errors.
        """
        try:
            return await self.__requestLayer(request, resolved_route)
        except ValidationException as exc:
            return await validation_response(exc, request, self.__default_responses)

    async def __requestLayer(
        self,
        request: Request,
        resolved_route: ResolvedRoute,
    ) -> Response:
        """
        Execute route-level middleware for the resolved route.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        resolved_route : ResolvedRoute
            Resolved route with matched handler and path parameters.

        Returns
        -------
        Response
            HTTP response produced by the pipeline or the handler.
        """
        stack = resolved_route.route.compiled_middlewares
        # Invoke the handler directly when no route middleware is configured.
        if not stack:
            return await self.__callHandler(resolved_route, request)

        instances = self.__middleware_cache.get(stack)
        if instances is None:
            built = [await self.__app.build(mw_class) for mw_class in stack]
            instances = tuple(built)
            self.__middleware_cache[stack] = instances

        if len(instances) == 1:
            return await instances[0].handle(
                request,
                _MiddlewareNext(self.__callHandler, (resolved_route, request)),
            )

        # Keep continuation state local to this request.
        pipeline = _MiddlewarePipeline(
            instances=instances,
            request=request,
            terminal=self.__callHandler,
            terminal_args=(resolved_route, request),
        )
        return await pipeline()

    async def __callHandler(
        self,
        resolved_route: ResolvedRoute,
        request: Request,
    ) -> Response:
        """
        Dispatch the request to the pre-resolved route handler.

        Uses boot-time dispatch tables keyed by route object identity,
        eliminating per-request module imports and attribute lookups.

        Parameters
        ----------
        resolved_route : ResolvedRoute
            Resolved route descriptor with handler reference and path params.
        request : Request
            Request-local parameters, including middleware changes.

        Returns
        -------
        Response
            HTTP response produced by the handler.

        Raises
        ------
        TypeError
            If the handler does not return a Response, dict, or msgspec.Struct.
        """
        route = resolved_route.route
        params = request.routeParams()
        route_id = id(route)
        fn = self.__fn_dispatch.get(route_id)

        if fn is not None:
            # Function-based route: invoke directly through the DI container.
            response = await self.__app.invoke(fn, **params)
        else:
            handler = self.__cls_dispatch.get(route_id)
            if handler is not None:
                # Use the application-owned service for built-in response routes.
                cls, method = handler
                instance = (
                    self.__default_responses
                    if cls is DefaultResponses
                    else await self.__app.build(cls)
                )
                response = await self.__app.call(
                    instance,
                    method,
                    **params,
                )
            else:
                # View route: render the template bound at boot time.
                response = await View.make(self.__view_dispatch[route_id])

        if isinstance(response, Response):
            return response

        # Serialize structured handler results as JSON.
        if isinstance(response, _JSON_RESPONSE_TYPES):
            return JSONResponse(status_code=200, content=response)

        error_msg = "Route handler must return a Response object"
        raise TypeError(error_msg)

    async def __callFallback(
        self,
        fallback: tuple,
    ) -> Response:
        """
        Invoke the registered fallback handler and return its response.

        Parameters
        ----------
        fallback : tuple
            Pair of ``(handler_class_or_callable, method_name_or_function)``.

        Returns
        -------
        Response
            HTTP response produced by the fallback handler.

        Raises
        ------
        TypeError
            If the fallback does not return a Response object.
        """
        _class, _method_or_func = fallback
        response = None
        if isinstance(_class, type) and isinstance(_method_or_func, str):
            # Class-based fallback: resolve the instance and call its method.
            instance = await self.__app.build(_class)
            response = await self.__app.call(instance, _method_or_func)
        elif callable(_method_or_func):
            # Function-based fallback: invoke directly through the container.
            response = await self.__app.invoke(_method_or_func)

        if not isinstance(response, Response):
            error_msg = "Fallback handler must return a Response object"
            raise TypeError(error_msg)

        return response

    async def __handleException(
        self,
        exc: Exception,
        request: object,
    ) -> Response:
        """
        Translate a caught exception into an HTTP response.

        Parameters
        ----------
        exc : Exception
            The exception raised during request processing.
        request : object
            Current request object (may be the raw transport adapter for
            pre-routing errors).

        Returns
        -------
        Response
            Appropriate HTTP response for the given exception type.
        """
        if isinstance(exc, PayloadTooLargeException):
            return await self.__default_responses.error(
                status_code=413,
                content="Request payload exceeds the configured limits.",
                expects_json=request.wantsJson(),
            )
        if isinstance(exc, ValidationException):
            # API routes always answer with the structured field errors; web
            # routes never reach this point (see __webTerminal).
            return await self.__default_responses.error(
                status_code=422,
                content=exc.error(),
                expects_json=True,
            )
        if isinstance(exc, RouteNotFound) and self.__fallback is not None:
            # Delegate unmatched routes to the registered fallback handler.
            return await self.__callFallback(self.__fallback)
        # Forward all other exceptions to the application failure handler.
        return await self.__catch.exception(exc, request)

    async def __bodyLengthResponse(self, adapter: TransportAdapter) -> Response | None:
        """
        Reject invalid framing and declared oversized bodies before reading.

        Parameters
        ----------
        adapter : TransportAdapter
            Incoming transport metadata.

        Returns
        -------
        Response | None
            A 400 or 413 response for rejected framing, otherwise None. Stream
            byte counting remains authoritative when length is absent or false.
        """
        headers = adapter.headers()
        raw_length = headers.get("content-length")
        if raw_length is None:
            return None
        length = raw_length.strip()
        if (
            headers.count("content-length") != 1
            or "transfer-encoding" in headers
            or not length.isascii() or not length.isdecimal()
        ):
            return await self.__default_responses.error(
                status_code=400, content="Invalid Content-Length framing.",
                expects_json=adapter.wantsJson(),
            )
        length = length.lstrip("0") or "0"
        maximum = str(self.__body_limits.max_body_size)
        if len(length) > len(maximum) or (
            len(length) == len(maximum) and length > maximum
        ):
            raise PayloadTooLargeException
        return None

    async def __processRequest(
        self,
        interface: Interface,
        adapter: TransportAdapter,
        receive_or_protocol: object,
        request_context: object,
    ) -> Response:
        """
        Build the HTTP response for this request.

        Runs global middleware, rate limiting, route resolution, and the
        handler pipeline.  All exceptions are delegated to
        ``__handleException``.

        Parameters
        ----------
        interface : Interface
            Transport interface type used to construct the BodyStream.
        adapter : TransportAdapter
            Protocol adapter carrying request metadata.
        receive_or_protocol : object
            ASGI receive callable or RSGI HTTPProtocol instance.
        request_context : object
            Active DI request scope for per-request bindings.

        Returns
        -------
        Response
            The fully constructed HTTP response.
        """
        # Tag the active scope with the HTTP kernel context identifier.
        request_context.set("kernel", _KERNEL_CONTEXT)  # type: ignore[union-attr]
        # Start the request timer only when the debug printer is active.
        if self.__printer_enabled:
            self.__request_printer.startTimer()

        # Use the transport adapter as the request placeholder for early errors.
        request = adapter
        try:
            # Execute global middleware and resolve packaged static assets.
            response = await self.__globalMiddleware(adapter)
            if response is None:
                response = await self.__bodyLengthResponse(adapter)
            if response is None and self.__rate_limit_enabled:
                response = await self.__rate_limit.handle(adapter)
            if response is not None:
                return response

            method = adapter.method()
            path = adapter.path()

            # Return an Allow header response for OPTIONS introspection requests.
            if method == "OPTIONS":
                allowed_methods = self.__routes.options(path)
                headers: dict[str, str] = {
                    "Allow": ", ".join(allowed_methods),
                }
                if "QUERY" in allowed_methods:
                    headers["Accept-Query"] = (
                        "application/json, application/x-www-form-urlencoded"
                    )
                return Response(status_code=200, headers=headers)

            # Resolve the route and construct the fully typed request object.
            resolved_route = self.__routes.resolve(method=method, path=path)
            request = Request(
                interface=interface,
                adapter=adapter,
                receive_or_protocol=receive_or_protocol,
                params=resolved_route.params,
                body_limits=self.__body_limits,
            )
            request_context[Request] = request  # type: ignore[index]

            # Dispatch through the web or API middleware pipeline.
            return await self.__routeLayer(request, resolved_route)

        except Exception as e:  # noqa: BLE001
            # Delegate all exceptions to the unified exception handler.
            return await self.__handleException(e, request)

    async def handleRSGI(
        self,
        scope: Scope,
        protocol: HTTPProtocol | WebsocketProtocol,
    ) -> object | None:
        """
        Handle an incoming RSGI HTTP request end-to-end.

        Parameters
        ----------
        scope : Scope
            Granian RSGI scope with connection metadata.
        protocol : HTTPProtocol
            RSGI protocol object for writing the response.

        Returns
        -------
        object | None
            Result of sending the RSGI response, or None on error.
        """
        adapter = RSGITransportAdapter(scope)
        if getattr(scope, "proto", "http") == "ws":
            return await self.__handleWebSocket(
                Interface.RSGI, adapter, protocol,
            )
        if not self.__request_slots.acquire(blocking=False):
            response = Response(
                status_code=503, headers={"Retry-After": "1"},
                content="HTTP request capacity exceeded.",
            )
            return await self.__rsgiResponse(adapter, response, protocol)
        try:
            async with self.__app.beginScope() as request_context:
                try:
                    response = await self.__processRequest(
                        Interface.RSGI, adapter, protocol, request_context,
                    )
                    return await self.__rsgiResponse(adapter, response, protocol)
                finally:
                    request = request_context[Request]
                    if isinstance(request, Request):
                        request.close()
        finally:
            self.__request_slots.release()

    async def handleASGI(
        self,
        scope: dict,
        receive: object,
        send: object,
    ) -> None:
        """
        Handle an incoming ASGI HTTP request end-to-end.

        Parameters
        ----------
        scope : dict
            ASGI connection scope dict with request metadata.
        receive : object
            ASGI receive callable for reading request body.
        send : object
            ASGI send callable for writing response messages.

        Returns
        -------
        None
        """
        adapter = ASGITransportAdapter(scope)
        if scope["type"] == "websocket":
            adapter["method"] = "GET"
            return await self.__handleWebSocket(
                Interface.ASGI, adapter, receive, send,
            )
        if not self.__request_slots.acquire(blocking=False):
            response = Response(
                status_code=503, headers={"Retry-After": "1"},
                content="HTTP request capacity exceeded.",
            )
            return await self.__asgiResponse(adapter, response, receive, send)
        try:
            async with self.__app.beginScope() as request_context:
                try:
                    response = await self.__processRequest(
                        Interface.ASGI, adapter, receive, request_context,
                    )
                    return await self.__asgiResponse(adapter, response, receive, send)
                finally:
                    request = request_context[Request]
                    if isinstance(request, Request):
                        request.close()
        finally:
            self.__request_slots.release()

    def __websocketOriginAllowed(self, adapter: TransportAdapter) -> bool:
        """
        Check browser origins before allowing an application handshake.

        Parameters
        ----------
        adapter : TransportAdapter
            Proxy-normalized handshake metadata.

        Returns
        -------
        bool
            True for missing Origin, same origin, or an explicit allowed origin.
        """
        origin = adapter.headers().get("origin")
        if not origin:
            return True
        origin = origin.lower().rstrip("/")
        allowed = self.__websocket_config.allow_origins
        if "*" in allowed or origin in allowed:
            return True
        scheme = adapter.scheme()
        scheme = {"ws": "http", "wss": "https"}.get(scheme, scheme)
        host = adapter.headers().get("host", "").lower()
        return bool(host) and origin == f"{scheme}://{host}"

    async def __callWebSocketHandler(
        self, resolved_route: ResolvedRoute, socket: WebSocket,
    ) -> None:
        """
        Invoke a preloaded connection handler through the scoped container.

        Parameters
        ----------
        resolved_route : ResolvedRoute
            Compiled route with converted parameters.
        socket : WebSocket
            Scoped connection injected into application handlers.

        Returns
        -------
        None
            Run the handler for the lifetime of the connection.

        Raises
        ------
        TypeError
            If the handler returns an HTTP response or another value.
        """
        route_id = id(resolved_route.route)
        function = self.__fn_dispatch.get(route_id)
        if function is not None:
            result = await self.__app.invoke(function, **socket.routeParams())
        else:
            controller, method = self.__cls_dispatch[route_id]
            instance = await self.__app.build(controller)
            result = await self.__app.call(instance, method, **socket.routeParams())
        if result is not None:
            error_msg = "WebSocket handlers must return None"
            raise TypeError(error_msg)

    async def __handleWebSocket(
        self,
        interface: Interface,
        adapter: TransportAdapter,
        receive_or_protocol: object,
        send: object = None,
    ) -> None:
        """
        Dispatch a bounded connection inside a dedicated lifetime scope.

        Parameters
        ----------
        interface : Interface
            Server protocol identifier.
        adapter : TransportAdapter
            Handshake request metadata.
        receive_or_protocol : object
            ASGI receive callback or Granian WebsocketProtocol.
        send : object, optional
            ASGI send callback, omitted for RSGI.

        Returns
        -------
        None
            Await the connection pipeline and always release admission.
        """
        socket = WebSocket(
            interface, adapter, receive_or_protocol, send,
            max_message_size=self.__websocket_config.max_message_size,
        )
        if not self.__websocket_slots.acquire(blocking=False):
            await socket.reject(status_code=503)
            return
        try:
            async with self.__app.beginScope() as connection_context:
                connection_context.set("kernel", _KERNEL_CONTEXT)
                connection_context[WebSocket] = socket
                try:
                    await self.__processWebSocket(adapter, socket)
                except WebSocketDisconnected:
                    pass
                except Exception:
                    if socket.accepted and interface is Interface.ASGI:
                        # Cleanup failure must not replace the handler's error.
                        with suppress(Exception):
                            await socket.close(code=1011)
                    raise
                finally:
                    if not socket.closed:
                        await socket.close()
        finally:
            self.__websocket_slots.release()

    async def __processWebSocket(
        self, adapter: TransportAdapter, socket: WebSocket,
    ) -> None:
        """
        Validate a handshake and run its connection middleware and handler.

        Parameters
        ----------
        adapter : TransportAdapter
            Handshake metadata for global guards and route matching.
        socket : WebSocket
            Connection already bound to the active application scope.

        Returns
        -------
        None
            Reject the handshake or await the application connection lifetime.

        Raises
        ------
        TypeError
            If middleware returns a value instead of None.
        """
        rejection = await self.__globalMiddleware(adapter)
        if rejection is None and self.__rate_limit_enabled:
            rejection = await self.__rate_limit.handle(adapter)
        if rejection is not None:
            status = rejection.getStatusCode()
            await socket.reject(
                status_code=status if status >= HTTPStatus.BAD_REQUEST else 404,
            )
            return
        if not self.__websocketOriginAllowed(adapter):
            await socket.reject()
            return
        try:
            resolved = self.__routes.resolve("WEBSOCKET", adapter.path())
        except (RouteNotFound, MethodNotAllowed):
            await socket.reject(status_code=404)
            return
        socket.routeParams().update(resolved.params)
        instances = tuple([ # NOSONAR
            await self.__app.build(middleware)
            for middleware in resolved.route.compiled_middlewares
        ])
        pipeline = _MiddlewarePipeline(
            instances, socket, self.__callWebSocketHandler, (resolved, socket),
        )
        result = await pipeline()
        if result is not None:
            error_msg = "WebSocket middleware must return None"
            raise TypeError(error_msg)
