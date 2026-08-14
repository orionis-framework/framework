import importlib
from functools import partial
from typing import TYPE_CHECKING
import msgspec
from orionis.console.output.http_request import HTTPRequestPrinter
from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.foundation.contracts.application import IApplication
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.request.rsgi import RSGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.contracts.kernel import IKernelHTTP
from orionis.http.default.responses import DefaultResponses
from orionis.http.enums.interfaces import Interface
from orionis.http.layer.shared.cors import CORSMiddleware
from orionis.http.layer.shared.maintenance import UnderMaintenanceMiddleware
from orionis.http.layer.shared.proxies import ProxiesMiddleware
from orionis.http.layer.shared.rate_limit import RateLimitMiddleware
from orionis.http.layer.shared.security import SecurityMiddleware
from orionis.http.layer.web.csrf_token import CSRFTokenMiddleware
from orionis.http.layer.web.start_session import StartSessionMiddleware
from orionis.http.payload.body import BodyStream
from orionis.http.request import Request
from orionis.http.response import JSONResponse, Response
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.loader import RouteLoader
from orionis.http.routes.route_resolver import RouteResolver
from orionis.http.validation import validation_response
from orionis.schemas.exceptions.validation import ValidationException

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from granian.rsgi import HTTPProtocol, Scope
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.routes.contracts.loader import IRouteLoader
    from orionis.http.routes.entities.resolved_route import ResolvedRoute

# Pre-built tuple for isinstance checks avoids per-call reconstruction.
_JSON_RESPONSE_TYPES: tuple[type, ...] = (dict, msgspec.Struct)

# Kernel context identifier reused across all request scopes.
_KERNEL_CONTEXT: KernelContext = KernelContext.HTTP

class _MiddlewarePipeline:
    """
    Iterative middleware pipeline that replaces per-request closure allocation.

    A single instance encapsulates the execution state for one middleware stack
    invocation.  Its ``__call__`` method acts as the ``next()`` callable passed
    to each layer, advancing the pipeline without allocating closures or cells
    per request.
    """

    __slots__ = (
        "_called_mask",
        "_depth",
        "_instances",
        "_n",
        "_request",
        "_terminal",
    )

    def __init__(
        self,
        instances: tuple,
        request: Request,
        terminal: Callable[[], Awaitable[Response]],
    ) -> None:
        """
        Store the middleware stack and terminal callable for one request.

        Parameters
        ----------
        instances : tuple
            Ordered tuple of pre-built middleware instances.
        request : Request
            Incoming HTTP request forwarded to each layer.
        terminal : Callable[[], Awaitable[Response]]
            Async callable invoked after all middleware layers have run.

        Returns
        -------
        None
        """
        self._instances = instances
        self._request = request
        self._terminal = terminal
        self._n = len(instances)
        self._depth = 0
        self._called_mask = 0

    async def __call__(self) -> Response:
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
        depth = self._depth
        # Reached the end of the stack; hand off to the terminal handler.
        if depth >= self._n:
            return await self._terminal()
        bit = 1 << depth
        # Guard against double invocation of next() from the same layer.
        if self._called_mask & bit:
            error_msg = "next() has already been called in this middleware layer."
            raise RuntimeError(error_msg)
        self._called_mask |= bit
        self._depth = depth + 1
        result = await self._instances[depth].handle(self._request, self)
        # Restore depth index after the layer returns.
        self._depth = depth
        return result

class KernelHTTP(IKernelHTTP):

    # ruff: noqa:TC001 - For Dependency injection

    __slots__ = (
        "__app",
        "__asgi_adapter",
        "__boot",
        "__catch",
        "__cls_dispatch",
        "__cors",
        "__default_responses",
        "__fallback",
        "__fn_dispatch",
        "__maintenance_enabled",
        "__middleware_cache",
        "__printer_enabled",
        "__proxies",
        "__rate_limit",
        "__rate_limit_enabled",
        "__request_printer",
        "__routes",
        "__rsgi_adapter",
        "__security",
        "__under_maintenance",
        "__web_middleware",
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
        # Per-route middleware stacks resolved at boot to avoid runtime container calls.
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

        # Ordered web-layer pipeline: session restoration then CSRF validation.
        self.__web_middleware: tuple = (
            await self.__app.build(StartSessionMiddleware),
            CSRFTokenMiddleware(config=self.__app.config("http").get("csrf", {})),
        )

        # Protocol-level response adapters for RSGI and ASGI transports.
        self.__rsgi_adapter = await self.__app.build(RSGIResponseAdapter)
        self.__asgi_adapter = await self.__app.build(ASGIResponseAdapter)

        # Request logger; only active when the application runs in debug mode.
        self.__request_printer = await self.__app.build(HTTPRequestPrinter)
        self.__request_printer.setEnabled(enabled=self.__app.isDebug())
        # Cache enabled flag to skip timer and log calls in the hot path.
        self.__printer_enabled: bool = self.__app.isDebug()

        # Resolve and cache the fallback handler to avoid per-request lookups.
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
        Eagerly import all route modules and resolve callables at boot time.

        Populates two int-keyed dispatch tables using route object identity,
        eliminating per-request module imports, attribute lookups, and tuple
        key construction from the handler invocation hot path.

        Returns
        -------
        None
        """
        fn_dispatch: dict[int, object] = {}
        cls_dispatch: dict[int, tuple[type, str]] = {}
        module_cache: dict[str, object] = {}

        # Walk every registered route once and store fully resolved callables.
        for route in self.__routes.allRoutes():
            action = route.action
            module_name = action["module"]
            module = module_cache.get(module_name)
            if module is None:
                module = importlib.import_module(module_name)
                module_cache[module_name] = module

            route_id = id(route)
            if route.type is RouteType.FUNCTION:
                fn_dispatch[route_id] = getattr(module, action["function"])
            else:
                cls_dispatch[route_id] = (
                    getattr(module, action["class"]),
                    action["method"],
                )

        self.__fn_dispatch: dict[int, object] = fn_dispatch
        self.__cls_dispatch: dict[int, tuple[type, str]] = cls_dispatch

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
        # Cache the maintenance flag to skip the check on the hot path.
        self.__maintenance_enabled = under_maintenance
        # Cache the limiter's enabled state to skip async overhead when disabled.
        self.__rate_limit_enabled = self.__rate_limit.isEnabled()

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

    def __globalMiddleware(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
        """
        Execute the synchronous global middleware chain on the request.

        Process request through middleware pipeline: proxies detection,
        security validation, and CORS negotiation.  Rate limiting is
        handled separately by the dispatcher because it is asynchronous.

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
        # Return 503 immediately when the application is in maintenance mode.
        if self.__maintenance_enabled:
            response = self.__under_maintenance.handle(adapter)
            if response is not None:
                return response
        # Enforce baseline security header policies.
        response = self.__security.handle(adapter)
        if response is not None:
            return response
        # Validate origin and handle CORS preflight requests.
        return self.__cors.before(adapter)

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
            stack = route.compiled_middlewares
            if stack and stack not in self.__middleware_cache:
                built = [await self.__app.build(mw_class) for mw_class in stack]
                self.__middleware_cache[stack] = tuple(built)

    async def __webLayer(
        self,
        request: Request,
        resolved_route: ResolvedRoute,
    ) -> Response:
        """
        Execute the web middleware pipeline for a web-group route.

        Runs StartSessionMiddleware then CSRFTokenMiddleware through a
        single-allocation iterative pipeline before delegating to
        ``__webTerminal``.

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
        # Single pipeline object replaces the recursive closure chain.
        pipeline = _MiddlewarePipeline(
            instances=self.__web_middleware,
            request=request,
            terminal=partial(self.__webTerminal, request, resolved_route),
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
        # Fast path: bypass pipeline construction when no route middleware exists.
        if not stack:
            return await self.__callHandler(resolved_route)

        instances = self.__middleware_cache.get(stack)
        if instances is None:
            built = [await self.__app.build(mw_class) for mw_class in stack]
            instances = tuple(built)
            self.__middleware_cache[stack] = instances

        # Single pipeline object replaces the recursive closure chain.
        pipeline = _MiddlewarePipeline(
            instances=instances,
            request=request,
            terminal=partial(self.__callHandler, resolved_route),
        )
        return await pipeline()

    async def __callHandler(
        self,
        resolved_route: ResolvedRoute,
    ) -> Response:
        """
        Dispatch the request to the pre-resolved route handler.

        Uses boot-time dispatch tables keyed by route object identity,
        eliminating per-request module imports and attribute lookups.

        Parameters
        ----------
        resolved_route : ResolvedRoute
            Resolved route descriptor with handler reference and path params.

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
        route_id = id(route)
        fn = self.__fn_dispatch.get(route_id)

        if fn is not None:
            # Function-based route: invoke directly through the DI container.
            response = await self.__app.invoke(fn, **resolved_route.params)
        else:
            # Class-based route: build the controller and call its action method.
            cls, method = self.__cls_dispatch[route_id]
            instance = await self.__app.build(cls)
            response = await self.__app.call(instance, method, **resolved_route.params)

        # Coerce dict and msgspec.Struct return values into JSON responses.
        if isinstance(response, _JSON_RESPONSE_TYPES):
            response = JSONResponse(status_code=200, content=response)

        if isinstance(response, Response):
            return response

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
        if isinstance(exc, ValidationException):
            # API routes always answer with the structured field errors; web
            # routes never reach this point (see __webTerminal).
            return self.__default_responses.error(
                status_code=422,
                content=exc.error(),
                expects_json=True,
            )
        if isinstance(exc, RouteNotFound) and self.__fallback is not None:
            # Delegate unmatched routes to the registered fallback handler.
            return await self.__callFallback(self.__fallback)
        # Forward all other exceptions to the application failure handler.
        return await self.__catch.exception(exc, request)

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
            # Execute the synchronous global middleware chain.
            response = self.__globalMiddleware(adapter)
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
            body_stream = BodyStream(
                interface=interface,
                receive_or_protocol=receive_or_protocol,
            )
            request = Request(
                interface=interface,
                adapter=adapter,
                body_stream=body_stream,
                params=resolved_route.params,
            )
            request_context[Request] = request  # type: ignore[index]

            # Dispatch through the web or API middleware pipeline.
            if resolved_route.kind == "web":
                return await self.__webLayer(request, resolved_route)
            return await self.__requestLayer(request, resolved_route)

        except Exception as e:  # noqa: BLE001
            # Delegate all exceptions to the unified exception handler.
            return await self.__handleException(e, request)

    async def handleRSGI(
        self,
        scope: Scope,
        protocol: HTTPProtocol,
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
        async with self.__app.beginScope() as request_context:
            response = await self.__processRequest(
                Interface.RSGI, adapter, protocol, request_context,
            )
            return await self.__rsgiResponse(adapter, response, protocol)

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
        async with self.__app.beginScope() as request_context:
            response = await self.__processRequest(
                Interface.ASGI, adapter, receive, request_context,
            )
            return await self.__asgiResponse(adapter, response, receive, send)
