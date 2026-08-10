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

class FluentRoute(IFluentRoute):

    _ALLOWED_METHODS = frozenset({
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
        action: Callable | list | type,
    ) -> None:
        """
        Initialize a FluentRoute instance.

        Parameters
        ----------
        method : str
            HTTP method (e.g., 'GET', 'POST').
        path : str
            Route path.
        action : Callable | list | type
            Action to execute. Three forms are accepted:

            * **Invokable controller** - bare class that defines ``__call__``::

                  FluentRoute("GET", "/", UserController)

            * **Controller + method** - two-element list::

                  FluentRoute("GET", "/", [UserController, "index"])

            * **Callable** - plain function or coroutine function::

                  FluentRoute("GET", "/", my_view)

        Returns
        -------
        None
            The instance is initialized; no value is returned.
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
        self.__method = method_upper
        self.__path = normalize_path(path)
        self.__id = RouteID.next(method_upper, self.__path)
        self.__class: type | None = None
        self.__handler: str | None = None
        self.__callable_handler: Callable | None = None
        self.__name: str | None = None
        self.__middleware: list[type[BaseMiddleware]] = []
        self.__without_middleware: set[type[BaseMiddleware]] = set()
        self.__kind: str = "web"

        # Parse the action and set the appropriate handler attributes
        _callable, _handler = parse_action(action)
        if _callable and _handler is None:
            self.__callable_handler = _callable
        else:
            self.__class = _callable
            self.__handler = _handler

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
        self.__name = name.strip()
        return self

    def middleware(
        self,
        *middleware: type[BaseMiddleware] | list | tuple | set,
    ) -> Self:
        """
        Add middleware to the route.

        Parameters
        ----------
        *middleware : type[BaseMiddleware] | list | tuple | set
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
        *middleware: type[BaseMiddleware] | list | tuple | set,
    ) -> Self:
        """
        Exclude one or more middleware classes from the route.

        Parameters
        ----------
        *middleware : type[BaseMiddleware] | list | tuple | set
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
        self.__path = normalize_path(prefix.rstrip("/") + "/" + self.__path.lstrip("/"))
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

    @property
    def _existingMiddleware(self) -> list:
        """Return the registered middleware list for the route."""
        return self.__middleware

    def export(self) -> dict:
        """
        Export the route configuration as a plain dictionary.

        Returns
        -------
        dict
            Dictionary with keys: id, method, path, class, handler,
            callable_handler, name, middleware, without_middleware, and kind.
        """
        return {
            "id": self.__id,
            "method": self.__method,
            "path": self.__path,
            "class": self.__class,
            "handler": self.__handler,
            "callable_handler": self.__callable_handler,
            "name": self.__name,
            "middleware": self.__middleware,
            "without_middleware": self.__without_middleware,
            "kind": self.__kind,
        }
