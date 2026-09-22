from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from re import Pattern

    from orionis.http.routes.enums.route_types import RouteType

@dataclass(slots=True, frozen=True)
class CompiledRoute:
    """
    Represent a runtime-ready compiled HTTP route.

    Attributes
    ----------
    path : str
        The original route path, e.g. ``'/users/{id:int}'``.
    method : str
        HTTP method in uppercase, e.g. ``'GET'``.
    type : RouteType
        How the handler will be resolved at dispatch time.
    action : dict
        Resolved handler descriptor containing ``module`` and either
        ``function`` (for functions) or ``class`` + ``method``
        (for controllers and invokable classes).
    name : str | None
        Optional route name used for URL generation.
    regex : Pattern | None
        Compiled regex for dynamic routes; ``None`` for static routes.
    segment_count : int
        Number of non-empty path segments, e.g. ``2`` for
        ``'/users/{id}'``. Used to narrow dynamic route matching to
        candidates of the same depth.
    priority_score : int
        Specificity score used to order dynamic routes during dispatch.
        Higher scores are matched first. Computed as
        ``static_segments * 10 - dynamic_segments``.
    kind : str
        Route group kind; either ``'web'`` or ``'api'``.
        Set by the loader when importing route files.
    converters : dict[str, Callable]
        Maps each path parameter name to its converter function.
        Empty for static routes.
    middleware : list
        Middleware classes attached to this route.
    without_middleware : set
        Middleware classes explicitly excluded from this route.
    compiled_middlewares : tuple
        Tuple of resolved middleware classes for efficient dispatch.
    """

    path: str
    method: str
    type: RouteType
    action: dict
    name: str | None
    regex: Pattern | None
    segment_count: int
    priority_score: int = 0
    kind: str = "web"
    converters: dict[str, Callable] = field(default_factory=dict)
    middleware: list = field(default_factory=list)
    without_middleware: set = field(default_factory=set)
    compiled_middlewares: tuple = field(default_factory=tuple)
