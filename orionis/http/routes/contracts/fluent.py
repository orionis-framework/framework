from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from orionis.http.routes.types import MiddlewareInput

class IFluentRoute(ABC):

    @property
    @abstractmethod
    def id(self) -> str:
        """
        Return the unique identifier of the route.

        Returns
        -------
        str
            The unique identifier of the route.
        """

    @abstractmethod
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
            This instance for method chaining.
        """

    @abstractmethod
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
            This instance for method chaining.
        """

    @abstractmethod
    def public(self, *, enabled: bool = True) -> Self:
        """Select a stateless route without automatic session or identity setup.

        Global security, CORS, rate limits, and explicitly attached middleware
        still run. Web session, CSRF, and automatic identity resolution do not.
        Use this profile only for endpoints that do not use cookie credentials.

        Parameters
        ----------
        enabled : bool, optional
            Whether to opt out of the default web or API context middleware.
            False explicitly retains that context inside a public group.

        Returns
        -------
        Self
            This route with the requested execution profile.

        Raises
        ------
        TypeError
            If enabled is not a boolean.
        """
    @abstractmethod
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
            This instance for method chaining.
        """

    @abstractmethod
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
            This instance for method chaining.
        """

    @abstractmethod
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
            This instance for method chaining.
        """

    @abstractmethod
    def export(self) -> dict:
        """
        Export a complete route configuration as a plain dictionary.

        Returns
        -------
        dict
            Dictionary with keys: id, method, path, class, handler,
            callable_handler, view, name, middleware, without_middleware,
            kind, and public.

        Raises
        ------
        ValueError
            If the route has neither a view nor an assigned action.
        """
