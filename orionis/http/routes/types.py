"""Define types for http routes."""

from collections.abc import Callable, Sequence
from collections.abc import Set as AbstractSet
from typing import TYPE_CHECKING, TypedDict
from orionis.http.routes.enums.protocols import RouteProtocol
from orionis.http.middleware import BaseMiddleware
from orionis.http.websocket_middleware import WebSocketMiddleware

if TYPE_CHECKING:
    from orionis.realtime.hub import Hub

# Callable represents Python functions here; parse_action rejects callable
# instances, bound methods, builtins and lambdas during registration.
type RouteAction = Callable | type | list[type | str] | tuple[type, str]
"""
Callable represents Python functions here; parse_action rejects callable instances,
bound methods, builtins and lambdas during registration.
"""
type MiddlewareInput = (
    type[BaseMiddleware | WebSocketMiddleware]
    | Sequence[type[BaseMiddleware | WebSocketMiddleware]]
    | AbstractSet[type[BaseMiddleware | WebSocketMiddleware]]
)
"""
Type alias for ``type[BaseMiddleware | WebSocketMiddleware] |
Sequence[type[BaseMiddleware | WebSocketMiddleware]] |
AbstractSet[type[BaseMiddleware | WebSocketMiddleware]]``.
"""


# The exported key "class" is a Python keyword.
ExportedRoute = TypedDict(
    "ExportedRoute",
    {
        "id": str,
        "method": str,
        "protocol": RouteProtocol,
        "path": str,
        "class": type | None,
        "handler": str | None,
        "callable_handler": Callable | None,
        "view": str | None,
        "hub": "type[Hub] | None",
        "hub_protocol": str | None,
        "name": str | None,
        "middleware": list[type[BaseMiddleware | WebSocketMiddleware]],
        "without_middleware": set[type[BaseMiddleware | WebSocketMiddleware]],
        "kind": str,
        "public": bool,
    },
)
"""HTTP or WebSocket route declaration, including its handler and middleware."""


class RouterExport(TypedDict):
    """Return value of the router registry's export method."""

    routes: list[ExportedRoute]
    """Route declarations in registration order."""
    fallback: tuple[type | None, Callable | str | None]
    """Controller and handler used when no registered route matches."""
