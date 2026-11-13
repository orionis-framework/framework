"""Define the contract for route resolver implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.routes.entities.resolved_route import ResolvedRoute


class IRouteResolver(ABC):
    """Define the contract for route resolver implementations."""

    @abstractmethod
    def resolve(
        self,
        method: str,
        path: str,
    ) -> ResolvedRoute:
        """
        Resolve a method and path into a compiled route.

        Parameters
        ----------
        method : str
            HTTP method string.
        path : str
            Raw request path.

        Returns
        -------
        orionis.http.routes.entities.resolved_route.ResolvedRoute
            Matched route and converted path parameters.

        Raises
        ------
        orionis.http.routes.exceptions.route_not_found.RouteNotFound
            Raise when no route matches the path.
        orionis.http.routes.exceptions.method_not_allowed.MethodNotAllowed
            Raise when the path exists under a different method.
        """

    @abstractmethod
    def options(self, path: str) -> list[str]:
        """
        Resolve all allowed methods for a path.

        Parameters
        ----------
        path : str
            Raw request path.

        Returns
        -------
        list[str]
            Sorted list of methods valid for the path.
        """

    @abstractmethod
    def fallback(self) -> tuple | None:
        """
        Return the registered fallback handler.

        Returns
        -------
        tuple | None
            Fallback descriptor or ``None`` if not registered.
        """

    @abstractmethod
    def allRoutes(self) -> list:
        """
        Return all compiled routes across all HTTP methods.

        Returns
        -------
        list[orionis.http.routes.entities.compiled_route.CompiledRoute]
            Deduplicated list of every registered compiled route.
        """

    @abstractmethod
    def invalidateCache(self) -> None:
        """
        Clear the hot-path cache.

        Returns
        -------
        None
            Remove all cached entries.
        """
