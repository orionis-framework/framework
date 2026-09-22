from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from orionis.http.routes.fluent import FluentRoute
    from orionis.http.routes.group import RouteGroup
    from orionis.http.routes.types import MiddlewareInput, RouteAction

class IRouter(ABC):

    @abstractmethod
    def auth(self) -> None:
        """Register the built-in web login, registration and logout routes.

        Returns
        -------
        None
            Routes are registered on this router.

        Raises
        ------
        ValueError
            If registration is attempted outside the web route context.
        """

    @abstractmethod
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
            Template name in dot notation (e.g. ``'welcome'``)

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """

    @abstractmethod
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

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """

    @abstractmethod
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

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """

    @abstractmethod
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

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """

    @abstractmethod
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

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """

    @abstractmethod
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

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """

    @abstractmethod
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

        Returns
        -------
        FluentRoute
            The registered FluentRoute instance.
        """

    @abstractmethod
    def fallback(
        self,
        action: RouteAction | None = None,
    ) -> None:
        """
        Register the fallback handler for unmatched routes (HTTP 404).

        Only one fallback may be registered; a second call raises
        ``FallbackRouteAlreadyRegisteredException``.

        Parameters
        ----------
        action : RouteAction | None, optional
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

    @abstractmethod
    def group(
        self,
        *,
        prefix: str | None = None,
        middleware: MiddlewareInput | None = None,
        without_middleware: MiddlewareInput | None = None,
        routes: Sequence[FluentRoute | RouteGroup] | None = None,
    ) -> RouteGroup:
        """
        Register a group of routes with a shared prefix and middleware.

        Parameters
        ----------
        prefix : str | None, optional
            URL prefix prepended to every route path in the group.
        middleware : MiddlewareInput | None, optional
            Middleware classes to attach to every route in the group.
            Accepts a single class or a container of classes.
        without_middleware : MiddlewareInput | None, optional
            Middleware classes to exclude from every route in the group.
            Accepts a single class or a container of classes.
        routes : Sequence[FluentRoute | RouteGroup] | None, optional
            Routes or nested groups to include.

        Returns
        -------
        RouteGroup
            Flattened membership for composition by another group.

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
            If membership contains neither routes nor groups.
        """

    @abstractmethod
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
