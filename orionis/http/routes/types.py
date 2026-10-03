from collections.abc import Callable, Sequence
from collections.abc import Set as AbstractSet
from orionis.http.middleware import BaseMiddleware
from orionis.http.websocket_middleware import WebSocketMiddleware

# Callable represents Python functions here; parse_action rejects callable
# instances, bound methods, builtins and lambdas during registration.
type RouteAction = Callable | type | list[type | str] | tuple[type, str]
type MiddlewareInput = (
    type[BaseMiddleware | WebSocketMiddleware]
    | Sequence[type[BaseMiddleware | WebSocketMiddleware]]
    | AbstractSet[type[BaseMiddleware | WebSocketMiddleware]]
)
