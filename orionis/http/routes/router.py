from typing import TYPE_CHECKING
from orionis.foundation.contracts.application import IApplication
from orionis.http.middleware import BaseMiddleware
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
        self.__fallback: tuple[Callable | None, Callable | None] = (
            None,
            None,
        )
        self.__routes: dict[str, FluentRoute] = {}
        self.__map_routes: dict[str, dict[str, str]] = {
            "GET": {},
            "POST": {},
            "PUT": {},
            "DELETE": {},
            "PATCH": {},
            "QUERY": {},
        }
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
        action: Callable | list | type | None = None,
    ) -> FluentRoute:
        """
        Create and register a single HTTP route.

        Parameters
        ----------
        method : str
            HTTP method (e.g. ``'GET'``, ``'POST'``).
        path : str
            URL path for the route.
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        # Normalise path before any duplicate check so that '/users' and
        # '/users/' are treated as the same route.
        normalized_path = normalize_path(path)
        method_upper = method.upper()

        # Replace default system routes when the user re-registers them.
        method_routes = self.__map_routes[method_upper]
        previously_registered_id = method_routes.get(normalized_path)
        if previously_registered_id and normalized_path in self._DEFAULT_PATHS:
            del self.__routes[previously_registered_id]
            del method_routes[normalized_path]

        # Create and store the new route
        fluent_router = (
            FluentRoute(method, path, action)._kind(self.__current_kind) # noqa: SLF001
        )
        self.__routes[fluent_router.id] = fluent_router
        method_routes[normalized_path] = fluent_router.id
        return fluent_router

    def __applyGroupToRoute(
        self,
        route: FluentRoute,
        prefix: str | None,
        middleware: list[type[BaseMiddleware]] | None,
        without_middleware: list[type[BaseMiddleware]] | None,
    ) -> None:
        """
        Apply a group prefix and middleware to a single route in place.

        Parameters
        ----------
        route : FluentRoute
            The route to modify.
        prefix : str | None
            URL prefix to prepend to the route path.
        middleware : list[type[BaseMiddleware]] | None
            Middleware classes to add, skipping any already on the route.
        without_middleware : list[type[BaseMiddleware]] | None
            Middleware classes to exclude from the route.

        Returns
        -------
        None
            The route is mutated in place; no value is returned.
        """
        if prefix:
            route.prefix(prefix)

        if middleware:
            existing = set(route._existingMiddleware)  # noqa: SLF001
            new_middleware = [
                mw for mw in middleware if mw not in existing
            ]
            if new_middleware:
                route.middleware(*new_middleware)

        if without_middleware:
            route.withOutMiddleware(*without_middleware)

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

    def post(
        self,
        path: str,
        action: Callable | list | type | None = None,
    ) -> FluentRoute:
        """
        Register a POST route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("POST", path, action)

    def query(
        self,
        path: str,
        action: Callable | list | type | None = None,
    ) -> FluentRoute:
        """
        Register a QUERY route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("QUERY", path, action)

    def get(
        self,
        path: str,
        action: Callable | list | type | None = None,
    ) -> FluentRoute:
        """
        Register a GET route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("GET", path, action)

    def put(
        self,
        path: str,
        action: Callable | list | type | None = None,
    ) -> FluentRoute:
        """
        Register a PUT route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("PUT", path, action)

    def delete(
        self,
        path: str,
        action: Callable | list | type | None = None,
    ) -> FluentRoute:
        """
        Register a DELETE route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("DELETE", path, action)

    def patch(
        self,
        path: str,
        action: Callable | list | type | None = None,
    ) -> FluentRoute:
        """
        Register a PATCH route.

        Parameters
        ----------
        path : str
            URL path for the route.
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """
        return self.__addSingleRoute("PATCH", path, action)

    def fallback(
        self,
        action: Callable | list | type | None = None,
    ) -> None:
        """
        Register the fallback handler for unmatched routes (HTTP 404/405).

        Only one fallback may be registered; a second call raises
        ``FallbackRouteAlreadyRegisteredException``.

        Parameters
        ----------
        action : Callable | list | type | None, optional
            Callable, invokable controller class (defining ``__call__``),
            or ``[ControllerClass, 'method_name']`` list.

        Returns
        -------
        None
            The fallback is stored on the instance; no value is returned.

        Raises
        ------
        FallbackRouteAlreadyRegisteredException
            If a fallback handler has already been registered.
        """
        if self.__fallback != (None, None):
            error_msg = (
                "Fallback route already registered. "
                "Only one fallback is allowed."
            )
            raise FallbackRouteAlreadyRegisteredException(error_msg)

        _callable, _handler = parse_action(action)
        if _callable and _handler is None:
            self.__fallback = (None, _callable)
        else:
            self.__fallback = (_callable, _handler)

    def group(
        self,
        *,
        prefix: str | None = None,
        middleware: type[BaseMiddleware] | list | tuple | set | None = None,
        without_middleware: (
            type[BaseMiddleware] | list | tuple | set | None
        ) = None,
        routes: list[FluentRoute] | None = None,
    ) -> None:
        """
        Register a group of routes with a shared prefix and middleware.

        Parameters
        ----------
        prefix : str | None, optional
            URL prefix prepended to every route path in the group.
        middleware : type[BaseMiddleware] | list | tuple | set | None, optional
            Middleware classes to attach to every route in the group.
            Accepts a single class or a container of classes.
        without_middleware : type[BaseMiddleware] | list | tuple | set | None, optional
            Middleware classes to exclude from every route in the group.
            Accepts a single class or a container of classes.
        routes : list[FluentRoute] | None, optional
            FluentRoute instances to include in the group.

        Returns
        -------
        None
            Routes are mutated and registered; no value is returned.

        Raises
        ------
        ValueError
            If *routes* is empty or ``None``.
        ValueError
            If *prefix* is not a ``str``.
        ValueError
            If any entry in *middleware* or *without_middleware* is not
            a ``BaseMiddleware`` subclass.
        TypeError
            If any entry in *routes* is not a ``FluentRoute`` instance.
        """
        if not routes:
            error_msg = (
                "Group routes must be provided as a list of "
                "FluentRoute instances."
            )
            raise ValueError(error_msg)

        if prefix and not isinstance(prefix, str):
            error_msg = "Group prefix must be a string if provided."
            raise ValueError(error_msg)

        try:
            group_middleware = (
                flatten_middleware(middleware) if middleware else None
            )
        except TypeError as exc:
            error_msg = (
                "Group middleware must be a BaseMiddleware subclass or "
                "a list/tuple/set of BaseMiddleware subclasses."
            )
            raise ValueError(error_msg) from exc

        try:
            group_without_middleware = (
                flatten_middleware(without_middleware)
                if without_middleware
                else None
            )
        except TypeError as exc:
            error_msg = (
                "Group without_middleware must be a BaseMiddleware "
                "subclass or a list/tuple/set of BaseMiddleware "
                "subclasses."
            )
            raise ValueError(error_msg) from exc

        for route in routes:
            if not isinstance(route, FluentRoute):
                error_msg = (
                    "All group routes must be instances of FluentRoute."
                )
                raise TypeError(error_msg)

            self.__applyGroupToRoute(
                route,
                prefix,
                group_middleware,
                group_without_middleware,
            )
            self.__routes[route.id] = route

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
        """
        routes = [r.export() for r in self.__routes.values()]
        return {
            "routes": routes,
            "fallback": self.__fallback,
        }
