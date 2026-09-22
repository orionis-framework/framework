from __future__ import annotations

from abc import ABC, abstractmethod


class IRouteLoader(ABC):

    @abstractmethod
    def load(self) -> dict[str, dict]:
        """
        Return all compiled routes, loading them first if necessary.

        Returns
        -------
        dict[str, dict]
            Mapping of HTTP method to a dict with keys ``'static'``
            (``{path: CompiledRoute}``) and ``'dynamic'``
            (``[CompiledRoute, ...]``).
        """

    @property
    @abstractmethod
    def fallback(self) -> tuple | None:
        """
        Return the registered fallback handler, if any.

        The fallback is used when no route matches the incoming request.
        Accessing this property triggers route loading if it has not
        already occurred.

        Returns
        -------
        tuple | None
            ``(class, method_name)`` for controller-based fallbacks,
            ``(None, callable)`` for callable-based fallbacks, or
            ``None`` if no fallback has been registered.
        """
