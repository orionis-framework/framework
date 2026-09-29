from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.routes.fluent import FluentRoute


@dataclass(frozen=True, slots=True)
class RouteGroup:
    """Hold already registered routes so a parent can compose their context.

    The immutable membership tuple is flattened at registration time. It is
    never retained by the compiler or traversed while serving a request.
    """

    routes: tuple[FluentRoute, ...]
