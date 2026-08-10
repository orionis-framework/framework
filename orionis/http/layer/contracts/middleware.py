from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

# No-arg async callable that advances to the next middleware layer
NextCallable = Callable[[], Awaitable["Response"]]

if TYPE_CHECKING:
    from orionis.http.request import Request
    from orionis.http.response import Response

class IBaseMiddleware(ABC):
    """Define the base contract for all HTTP middlewares in the pipeline.

    Middlewares are executed in a chain (onion model), where each
    middleware can inspect or modify the request, delegate to the next
    middleware in the chain, and inspect or modify the response.
    """

    __slots__ = ()

    @abstractmethod
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
        """Process an incoming HTTP request and delegate to next handler.

        Parameters
        ----------
        request : Request
            Incoming HTTP request instance.
        call_next : NextCallable
            No-arg async callable that advances to the next middleware
            or final route handler in the pipeline.

        Returns
        -------
        Response
            Final HTTP response object.
        """
