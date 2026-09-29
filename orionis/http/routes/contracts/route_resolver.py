from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.routes.entities.resolved_route import ResolvedRoute

class IRouteResolver(ABC):

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
        ResolvedRoute
            Matched route and converted path parameters.

        Raises
        ------
        RouteNotFound
            Raise when no route matches the path.
        MethodNotAllowed
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

        Parameters
        ----------
        None
            This method does not accept parameters.

        Returns
        -------
        tuple | None
            Fallback descriptor or ``None`` if not registered.
        """

    @abstractmethod
    def allRoutes(self) -> list:
        """
        Return all compiled routes across all HTTP methods.

        Parameters
        ----------
        None
            This method does not accept parameters.

        Returns
        -------
        list[CompiledRoute]
            Deduplicated list of every registered compiled route.
        """

    @abstractmethod
    def invalidateCache(self) -> None:
        """
        Clear the hot-path cache.

        Parameters
        ----------
        None
            This method does not accept parameters.

        Returns
        -------
        None
            Remove all cached entries.
        """
