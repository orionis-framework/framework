from collections.abc import Sequence
from itertools import chain
from typing import TYPE_CHECKING
from orionis.auth.middleware.authenticate import AuthenticateSessionMiddleware
from orionis.auth.middleware.guest import GuestMiddleware
from orionis.foundation.contracts.application import IApplication
from orionis.http.default.responses import DefaultResponses
from orionis.http.routes.contracts.router import IRouter
from orionis.http.routes.exceptions.fallback_route_already_registered import (
    FallbackRouteAlreadyRegisteredException,
)
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.functions import (
    flatten_middleware,
    normalize_path,
    parse_action,
)
from orionis.http.routes.group import RouteGroup
from orionis.http.routes.types import MiddlewareInput, RouteAction

if TYPE_CHECKING:
    from collections.abc import Callable

class Router(IRouter):

    # ruff: noqa: TC001 (DI)

    _DEFAULT_PATHS = frozenset({
        "/favicon.ico",
        "/robots.txt",
        "/sitemap.xml",
    })

    def __init__(
        self,
        app: IApplication,
    ) -> None:
        """
        Initialise the Router and register default system routes.

        Parameters
        ----------
        app : IApplication
            The application instance.

        Returns
        -------
        None
            State is stored on the instance; no value is returned.
        """
        self.__app = app
        self.__fallback: tuple[type | None, Callable | str | None] = (
            None,
            None,
        )
        self.__routes: dict[str, FluentRoute] = {}
        self.__replaceable_routes: dict[str, FluentRoute] = {}
        self.__current_kind: str = "web"
        self.__defaultRoutes()

    def __defaultRoutes(self) -> None:
        """
        Register default routes for common static paths.

        Registers GET handlers for favicon, robots.txt, and sitemap.xml
        using the DefaultResponses class.

        Parameters
        ----------
        None

        Returns
        -------
        None
            Default routes are registered on the instance;
            no value is returned.
        """
        self.get("/favicon.ico", [DefaultResponses, "favicon"])
        self.get("/robots.txt", [DefaultResponses, "robotsTxt"])
        self.get("/sitemap.xml", [DefaultResponses, "sitemapXml"])
        self.get(self.__app.routeHealthCheck, [DefaultResponses, "health"])

    def __addSingleRoute(
        self,
        method: str,
        path: str,
        action: RouteAction | None = None,
        *,
        view: str | None = None,
    ) -> FluentRoute:
        """
        Create and register a single HTTP route.

        Parameters
        ----------
        method : str
            HTTP method (e.g. ``'GET'``, ``'POST'``).
        path : str
            URL path for the route.
        action : RouteAction | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.
            If omitted or None, call ``action(controller, handler)`` on the
            returned route before exporting the router.
        view : str | None, optional
            Template name rendered directly by the kernel, used instead of
            *action* for view-only routes.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        fluent_route = (
            FluentRoute(method, path, action, view=view)._kind(self.__current_kind) # noqa: SLF001
        )
        normalized_path = fluent_route.path
        if method == "GET" and normalized_path in self._DEFAULT_PATHS:
            previous = self.__replaceable_routes.get(normalized_path)
            if previous is not None and previous.path == normalized_path:
                del self.__routes[previous.id]
            self.__replaceable_routes[normalized_path] = fluent_route
        self.__routes[fluent_route.id] = fluent_route
        return fluent_route

    def _setKind(self, kind: str) -> None:
        """
        Set the route group kind context for subsequent registrations.

        All routes registered after this call will carry the given
        *kind* value (``'web'`` or ``'api'``) in their exported dict.
        The loader calls this before importing each route file so that
        the routes defined in that file are tagged accordingly.

        Parameters
        ----------
        kind : str
            Route group kind, either ``'web'`` or ``'api'``.

        Returns
        -------
        None
            Context is updated in place; no value is returned.
        """
        self.__current_kind = kind

    def auth(
        self,
        login_controller: type | None = None,
        register_controller: type | None = None,
    ) -> None:
        """Register the built-in web login, registration and logout routes.

        Call once from a web route file. Login and registration accept guests;
        logout requires a session identity and accepts POST only. Session and
        CSRF middleware are supplied by the kernel's web pipeline.

        Returns
        -------
        None
            Registers GET/POST login and sign-up plus POST logout. The POST
            routes are named ``login``, ``register`` and ``logout``.

        Raises
        ------
        ValueError
            If registration is attempted outside the web route context.
        """
        # Ensure that the auth routes are only registered within the web context.
        if self.__current_kind != "web":
            error_msg = "Route.auth() must be declared in a web route file."
            raise ValueError(error_msg)

        # Load built-in controllers only when their routes are requested.
        login = login_controller
        if login is None:
            from orionis.http.default.controllers.login_controller import (  # noqa: PLC0415
                LoginController,
            )
            login = LoginController

        register = register_controller
        if register is None:
            from orionis.http.default.controllers.register_controller import (  # noqa: PLC0415
                RegisterController,
            )
            register = RegisterController

        # Register the auth routes with the appropriate middleware and controllers.
        self.group(middleware=GuestMiddleware, routes=[
            self.get("/login", [login, "index"]),
            self.post("/login", [login, "login"]).name("login"),
            self.get("/sign-up", [register, "index"]),
            self.post("/sign-up", [register, "register"]).name("register"),
        ])
        self.post("/logout", [login, "logout"]).name("logout").middleware(
            AuthenticateSessionMiddleware,
        )

    def view(
        self,
        path: str,
        view: str,
    ) -> FluentRoute:
        """
        Register a GET route that renders a template with no controller.

        Parameters
        ----------
        path : str
            URL path for the route.
        view : str
            Template name in dot notation (e.g. ``'welcome'``) or a
            relative path (e.g. ``'pages/welcome.html'``).

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.

        Raises
        ------
        ValueError
            If ``view`` is not a non-empty string.
        """
        if not isinstance(view, str) or not view.strip():
            error_msg = "View name must be a non-empty string"
            raise ValueError(error_msg)

        return self.__addSingleRoute("GET", path, view=view.strip())

    def post(
        self,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """
        Register a POST route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : RouteAction | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.
            If omitted or None, call ``action(controller, handler)`` on the
            returned route before exporting the router.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("POST", path, action)

    def query(
        self,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """
        Register a QUERY route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : RouteAction | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.
            If omitted or None, call ``action(controller, handler)`` on the
            returned route before exporting the router.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("QUERY", path, action)

    def get(
        self,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """
        Register a GET route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : RouteAction | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.
            If omitted or None, call ``action(controller, handler)`` on the
            returned route before exporting the router.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("GET", path, action)

    def put(
        self,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """
        Register a PUT route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : RouteAction | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.
            If omitted or None, call ``action(controller, handler)`` on the
            returned route before exporting the router.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("PUT", path, action)

    def delete(
        self,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """
        Register a DELETE route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : RouteAction | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.
            If omitted or None, call ``action(controller, handler)`` on the
            returned route before exporting the router.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("DELETE", path, action)

    def patch(
        self,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """
        Register a PATCH route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : RouteAction | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.
            If omitted or None, call ``action(controller, handler)`` on the
            returned route before exporting the router.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("PATCH", path, action)

    def fallback(
        self,
        action: RouteAction,
    ) -> None:
        """
        Register the fallback handler for unmatched routes (HTTP 404).

        Only one fallback may be registered; a second call raises
        ``FallbackRouteAlreadyRegisteredException``.

        Parameters
        ----------
        action : RouteAction
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list. Required because
            fallback registration does not return a fluent route builder.

        Returns
        -------
        None
            The fallback is stored on the instance; no value is returned.

        Raises
        ------
        FallbackRouteAlreadyRegisteredException
            If a fallback handler has already been registered.
        TypeError
            If the action is None or is not an accepted handler form.
        ValueError
            If a controller pair has an invalid length or names a missing
            method.
        """
        if self.__fallback != (None, None):
            error_msg = (
                "Fallback route already registered. "
                "Only one fallback is allowed."
            )
            raise FallbackRouteAlreadyRegisteredException(error_msg)

        _callable, _handler = parse_action(action)
        if isinstance(_callable, type) and _handler is None:
            self.__fallback = (_callable, "__call__")
        elif _handler is None:
            self.__fallback = (None, _callable)
        else:
            self.__fallback = (_callable, _handler)

    def group(
        self,
        *,
        prefix: str | None = None,
        middleware: MiddlewareInput | None = None,
        without_middleware: MiddlewareInput | None = None,
        routes: Sequence[FluentRoute | RouteGroup] | None = None,
    ) -> RouteGroup:
        """Compose a group and return its flattened membership for nesting.

        Parameters
        ----------
        prefix : str | None, optional
            Prefix prepended to every descendant path.
        middleware : MiddlewareInput | None, optional
            Parent middleware executed before descendant middleware.
        without_middleware : MiddlewareInput | None, optional
            Exclusions applied to the final compiled middleware stack.
        routes : Sequence[FluentRoute | RouteGroup] | None, optional
            Routes or groups already registered by inner expressions.

        Returns
        -------
        RouteGroup
            Already registered routes, usable as members of another group.

        Raises
        ------
        ValueError
            If the group is empty, its context is invalid, or a route appears
            more than once. Validation completes before any route is changed.
        TypeError
            If membership is not a sequence of routes and groups.
        """
        members = self.__groupMembers(routes)
        if prefix is not None and not isinstance(prefix, str):
            error_msg = "Group prefix must be a string if provided."
            raise ValueError(error_msg)
        normalized_prefix = normalize_path(prefix).rstrip("/") if prefix else ""
        try:
            parent_middleware = tuple(
                flatten_middleware(middleware) if middleware is not None else (),
            )
            excluded = frozenset(
                flatten_middleware(without_middleware)
                if without_middleware is not None else (),
            )
        except TypeError as exc:
            error_msg = (
                "Group middleware and without_middleware must contain "
                "BaseMiddleware subclasses."
            )
            raise ValueError(error_msg) from exc

        for route in members:
            route.inheritGroup(normalized_prefix, parent_middleware, excluded)
            self.__routes[route.id] = route
        return RouteGroup(members)

    @staticmethod
    def __groupMembers(
        routes: Sequence[FluentRoute | RouteGroup] | None,
    ) -> tuple[FluentRoute, ...]:
        """Validate and flatten membership without mutating any routes.

        Returns
        -------
        tuple[FluentRoute, ...]
            Unique leaf routes in declaration order.

        Raises
        ------
        ValueError
            If membership is empty or contains duplicate routes.
        TypeError
            If a member is neither a route nor a group.
        """
        if routes is not None and (
            not isinstance(routes, Sequence)
            or isinstance(routes, (str, bytes, bytearray))
        ):
            error_msg = "Group routes must be a sequence of routes or groups."
            raise TypeError(error_msg)
        if not routes:
            error_msg = "Group routes must not be empty."
            raise ValueError(error_msg)
        members: list[FluentRoute] = []
        seen: set[str] = set()
        leaves = chain.from_iterable(
            member.routes if isinstance(member, RouteGroup) else (member,)
            for member in routes
        )
        for route in leaves:
            if not isinstance(route, FluentRoute):
                error_msg = "Group members must be FluentRoute or RouteGroup instances."
                raise TypeError(error_msg)
            if route.id in seen:
                error_msg = "A route must occur only once within a group."
                raise ValueError(error_msg)
            seen.add(route.id)
            members.append(route)
        if not members:
            error_msg = "Group routes must not be empty."
            raise ValueError(error_msg)
        return tuple(members)

    def export(self) -> dict:
        """
        Export all registered routes and the fallback handler.

        Returns
        -------
        dict
            A dictionary with two keys:

            - ``'routes'``: list of all registered routes as dicts.
            - ``'fallback'``: tuple
              ``(class_or_None, handler_or_callable)``.

        Raises
        ------
        ValueError
            If a registered route still has no action or view.
        """
        routes = [r.export() for r in self.__routes.values()]
        return {
            "routes": routes,
            "fallback": self.__fallback,
        }
