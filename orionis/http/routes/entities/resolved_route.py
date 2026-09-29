from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from orionis.http.routes.entities.compiled_route import CompiledRoute

_EMPTY_PARAMS = MappingProxyType({})

@dataclass(slots=True, frozen=True)
class ResolvedRoute:
    """
    Represent the immutable result of a successful route resolution.

    Attributes
    ----------
    route : CompiledRoute
        The matched compiled route descriptor.
    params : Mapping[str, Any]
        Path parameters extracted and type-converted from the URL.
        Empty for static routes.
    """

    route: CompiledRoute
    params: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Freeze parameters so cached results can be shared across requests."""
        params = MappingProxyType(dict(self.params)) if self.params else _EMPTY_PARAMS
        object.__setattr__(self, "params", params)

    @classmethod
    def _fromOwnedParams(
        cls,
        route: CompiledRoute,
        params: dict[str, Any],
    ) -> ResolvedRoute:
        """Freeze a parameter dict exclusively owned by the route resolver.

        Callers must discard all mutable references to the supplied dict.
        The public constructor continues to copy externally owned mappings.

        Returns
        -------
        ResolvedRoute
            A route result wrapping the transferred parameter mapping.
        """
        result = object.__new__(cls)
        object.__setattr__(result, "route", route)
        object.__setattr__(result, "params", MappingProxyType(params))
        return result

    @property
    def kind(self) -> str:
        """
        Return the route group kind (``'web'`` or ``'api'``).

        Delegates to the underlying :attr:`route.kind` field so that
        callers never need to reach into the compiled route directly.

        Returns
        -------
        str
            Either ``'web'`` or ``'api'``.
        """
        return self.route.kind
