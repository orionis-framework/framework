from collections.abc import Callable, Sequence
from collections.abc import Set as AbstractSet

from orionis.http.middleware import BaseMiddleware

type RouteAction = Callable | type | list[type | str] | tuple[type, str]
type MiddlewareInput = (
    type[BaseMiddleware]
    | Sequence[type[BaseMiddleware]]
    | AbstractSet[type[BaseMiddleware]]
)
