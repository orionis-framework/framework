from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import re
    from collections.abc import Callable

class IRouteCompiler(ABC):

    @abstractmethod
    def compile(
        self,
        routes: list[dict],
        fallback: tuple | None,
        app_middleware: list[type] | None = None,
    ) -> tuple[dict[str, dict], tuple | None]:
        """
        Compile a list of raw route dicts into a ready-to-dispatch structure.

        Parameters
        ----------
        routes : list[dict]
            Raw route dicts as returned by ``Router.export()["routes"]``.
        fallback : tuple | None
            Raw fallback tuple from ``Router.export()["fallback"]``.
        app_middleware : list[type] | None, optional
            Global middleware classes to prepend to every route's middleware
            stack before route-specific middleware is applied.

        Returns
        -------
        tuple[dict[str, dict], tuple | None]
            A pair ``(compiled_routes, fallback)`` where
            ``compiled_routes`` maps each HTTP method to
            ``{"static": {path: CompiledRoute},
            "dynamic": [CompiledRoute, ...]}``. Dynamic lists are
            sorted descending by ``priority_score`` so more-specific
            patterns are matched first.

        Raises
        ------
        ValueError
            If two dynamic routes produce the same structural URL
            pattern (collision).
        TypeError
            If an invokable class does not define ``__call__``.
        """

    @staticmethod
    @abstractmethod
    def compilePath(
        path: str,
    ) -> tuple[bool, re.Pattern | None, dict[str, Callable]]:
        """
        Determine whether a path is static or dynamic and compile its regex.

        This method is intentionally public so that :class:`RouteCache`
        can call it during cache deserialisation to reconstruct ``regex``
        and ``converters`` without ever persisting callable objects.

        Parameters
        ----------
        path : str
            The route path, e.g. ``'/users/{id:int}'``.

        Returns
        -------
        tuple[bool, re.Pattern | None, dict[str, Callable]]
            ``(is_static, regex, converters)`` — ``regex`` and
            ``converters`` are ``None`` / empty for static paths.
        """
