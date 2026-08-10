from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.http.layer.contracts.middleware import IBaseMiddleware, NextCallable

if TYPE_CHECKING:
    from orionis.http.request import Request
    from orionis.http.response import Response

class BaseMiddleware(IBaseMiddleware):
    """Base class for HTTP middleware implementations."""

    __slots__ = ()

    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
        """
        Process an incoming HTTP request and delegate to next handler.

        Subclasses must override this method to add before/after logic,
        middleware-specific handling, or early returns. This base
        implementation raises NotImplementedError to enforce proper
        implementation in subclasses.

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
            HTTP response object returned by the next handler.

        Raises
        ------
        NotImplementedError
            Always raised as subclasses must implement this method.
        """
        # Subclasses must implement the handle method
        error_msg = (
            f"{self.__class__.__name__} must implement the handle() "
            "method"
        )
        raise NotImplementedError(error_msg)
