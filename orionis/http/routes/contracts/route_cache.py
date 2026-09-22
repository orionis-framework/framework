from __future__ import annotations

from abc import ABC, abstractmethod


class IRouteCache(ABC):

    @abstractmethod
    def toCache(
        self,
        routes: dict[str, dict],
        fallback: tuple | None,
    ) -> dict:
        """
        Serialise compiled routes and the fallback handler to a cache dict.

        Parameters
        ----------
        routes : dict[str, dict]
            Compiled routes mapping produced by ``RouteCompiler.compile``.
        fallback : tuple | None
            Raw fallback tuple stored by the loader.

        Returns
        -------
        dict
            JSON-safe representation suitable for
            ``FileBasedCache.save()``.
        """

    @abstractmethod
    def fromCache(
        self,
        cached: dict,
    ) -> tuple[dict[str, dict], tuple | None]:
        """
        Rebuild compiled routes and the fallback handler from a cache dict.

        Parameters
        ----------
        cached : dict
            Dict previously produced by :meth:`toCache`.

        Returns
        -------
        tuple[dict[str, dict], tuple | None]
            ``(routes, fallback)`` ready to be stored on the loader.
        """
