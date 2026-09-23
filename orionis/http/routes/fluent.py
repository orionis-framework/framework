from __future__ import annotations
from typing import TYPE_CHECKING, Self
from orionis.http.routes.contracts.fluent import IFluentRoute
from orionis.http.routes.functions import (
    flatten_middleware,
    normalize_path,
    parse_action,
)
from orionis.http.routes.route_id import RouteID

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.http.middleware import BaseMiddleware
    from orionis.http.routes.types import MiddlewareInput, RouteAction

class FluentRoute(IFluentRoute):

    _ALLOWED_METHODS: frozenset[str] = frozenset({
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "QUERY",
    })

    def __init__(
        self,
        method: str,
        path: str,
        action: RouteAction | None = None,
        *,
        view: str | None = None,
    ) -> None:
        """
        Initialize a FluentRoute instance.

        Parameters
        ----------
        method : str
            HTTP method (e.g., 'GET', 'POST').
        path : str
            Route path.
        action : RouteAction | None, optional
            Action to execute. Three forms are accepted:

            * **Invokable controller** - bare class that defines ``__call__``::

                  FluentRoute("GET", "/", UserController)

            * **Controller + method** - two-element list::

                  FluentRoute("GET", "/", [UserController, "index"])

            * **Callable** - plain function or coroutine function::

                  FluentRoute("GET", "/", my_view)

            Ignored when *view* is provided. If omitted or None, set the
            controller and method with ``action()`` before exporting.
        view : str | None, optional
            Template name rendered directly by the kernel. When given, the
            route carries no Python handler and *action* is not parsed.

        Returns
        -------
        None
            The instance is initialized; no value is returned.

        Raises
        ------
        TypeError
            If method or path is not a string, or a supplied action is invalid.
        ValueError
            If method is unsupported, view is invalid, or a controller pair
            has an invalid length or names a missing method.
        """
        # Validate the method and path parameters
        if not isinstance(method, str):
            error_msg = "HTTP method must be a string"
            raise TypeError(error_msg)
        method_upper = method.upper()
        if method_upper not in self._ALLOWED_METHODS:
            error_msg = (
                f"Invalid HTTP method: {method}. "
                f"Allowed methods are: {', '.join(self._ALLOWED_METHODS)}"
            )
            raise ValueError(error_msg)
        if not isinstance(path, str):
            error_msg = "Path must be a string"
            raise TypeError(error_msg)

        # Initialize route attributes
        self.__method: str = method_upper
        self.__path: str = normalize_path(path)
        self.__id: str = RouteID.next(method_upper, self.__path)
        self.__class: type | None = None
        self.__handler: str | None = None
        self.__callable_handler: Callable | None = None
        self.__name: str | None = None
        self.__middleware: list[type[BaseMiddleware]] = []
        self.__without_middleware: set[type[BaseMiddleware]] = set()
        self.__kind: str = "web"
        self.__view: str | None = view

        # A view route is rendered by the kernel and has no Python handler.
        if view is not None:
            if not isinstance(view, str) or not view.strip():
                error_msg = "View name must be a non-empty string"
                raise ValueError(error_msg)
            self.__view = view.strip()
            return

        # Allow the fluent action setter to complete registration later.
        if action is None:
            return

        # Parse the action and set the appropriate handler attributes
        _callable, _handler = parse_action(action)
        if _callable and _handler is None:
            self.__callable_handler = _callable
        else:
            self.__class = _callable
            self.__handler = _handler

    @property
    def path(self) -> str:
        """Return the current canonical path, including inherited prefixes."""
        return self.__path

    @property
    def id(self) -> str:
        """
        Return the unique identifier of the route.

        Returns
        -------
        str
            The unique identifier of the route.
        """
        return self.__id

    def action(self, controller: type, handler: str) -> Self:
        """
        Set the controller class and handler for the route.

        Parameters
        ----------
        controller : type
            Controller class to associate with the route.
        handler : str
            Name of the handler method.

        Returns
        -------
        Self
            This FluentRoute instance for method chaining.
        """
        _callable, _handler = parse_action([controller, handler])
        self.__class = _callable
        self.__handler = _handler
        self.__callable_handler = None
        self.__view = None
        return self

    def name(self, name: str) -> Self:
        """
        Set the name for the route.

        Parameters
        ----------
        name : str
            Name to assign to the route.

        Returns
        -------
        Self
            This FluentRoute instance for method chaining.
        """
        if not isinstance(name, str):
            error_msg = "Route name must be a string"
            raise TypeError(error_msg)
        if not name.strip():
            error_msg = "Route name must not be empty"
            raise ValueError(error_msg)
        self.__name = name.strip()
        return self

    def middleware(
        self,
        *middleware: MiddlewareInput,
    ) -> Self:
        """
        Add middleware to the route.

        Parameters
        ----------
        *middleware : MiddlewareInput
            One or more middleware classes (not instances) to attach.
            Classes may be passed individually or wrapped in a
            ``list``, ``tuple`` or ``set``.

        Returns
        -------
        Self
            This FluentRoute instance for method chaining.
        """
        self.__middleware.extend(flatten_middleware(*middleware))
        return self

    def withOutMiddleware(
        self,
        *middleware: MiddlewareInput,
    ) -> Self:
        """
        Exclude one or more middleware classes from the route.

        Parameters
        ----------
        *middleware : MiddlewareInput
            One or more middleware classes to exclude from this route.
            Classes may be passed individually or wrapped in a
            ``list``, ``tuple`` or ``set``.

        Returns
        -------
        Self
            This FluentRoute instance for method chaining.
        """
        self.__without_middleware.update(flatten_middleware(*middleware))
        return self

    def prefix(self, prefix: str) -> Self:
        """
        Prepend a path segment to the route's current path.

        Parameters
        ----------
        prefix : str
            The path prefix to prepend.

        Returns
        -------
        Self
            This FluentRoute instance for method chaining.
        """
        if not isinstance(prefix, str):
            error_msg = "Prefix must be a string"
            raise TypeError(error_msg)
        normalized = normalize_path(prefix).rstrip("/")
        self.__path = (
            normalized + self.__path if self.__path != "/" else normalized or "/"
        )
        return self

    def inheritGroup(
        self,
        prefix: str,
        middleware: tuple[type[BaseMiddleware], ...],
        without_middleware: frozenset[type[BaseMiddleware]],
    ) -> Self:
        """Apply validated group context during registration.

        Parameters
        ----------
        prefix : str
            Canonical prefix without a trailing slash, or an empty string.
        middleware : tuple[type[BaseMiddleware], ...]
            Parent middleware, in declaration order.
        without_middleware : frozenset[type[BaseMiddleware]]
            Exclusions inherited by the route.

        Returns
        -------
        Self
            This route with the parent context prepended.
        """
        if prefix:
            self.__path = prefix + self.__path if self.__path != "/" else prefix
        # The compiler removes duplicates after all parent layers are known.
        self.__middleware[:0] = middleware
        self.__without_middleware.update(without_middleware)
        return self

    def _kind(self, kind: str) -> Self:
        """
        Set the kind of the route (e.g., 'web', 'api').

        Parameters
        ----------
        kind : str
            The kind to set for the route.

        Returns
        -------
        Self
            This FluentRoute instance for method chaining.
        """
        if not isinstance(kind, str):
            error_msg = "Kind must be a string"
            raise TypeError(error_msg)
        self.__kind = kind.strip().lower()
        return self

    def export(self) -> dict:
        """
        Export a complete route configuration as a plain dictionary.

        Returns
        -------
        dict
            Dictionary with keys: id, method, path, class, handler,
            callable_handler, view, name, middleware, without_middleware,
            and kind.

        Raises
        ------
        ValueError
            If the route has neither a view nor an assigned action.
        """
        if (
            self.__view is None
            and self.__callable_handler is None
            and self.__class is None
        ):
            error_msg = (
                f"Route {self.__method} '{self.__path}' has no action. "
                "Call .action(controller, handler) before exporting routes."
            )
            raise ValueError(error_msg)
        return {
            "id": self.__id,
            "method": self.__method,
            "path": self.__path,
            "class": self.__class,
            "handler": self.__handler,
            "callable_handler": self.__callable_handler,
            "view": self.__view,
            "name": self.__name,
            "middleware": self.__middleware,
            "without_middleware": self.__without_middleware,
            "kind": self.__kind,
        }
