import secrets
from orionis.http import BaseMiddleware, NextCallable, Request, Response

class RequestIDMiddleware(BaseMiddleware):
    """Attach a unique correlation identifier to every incoming request."""

    __slots__ = ()

    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
        """
        Process an incoming HTTP request and delegate to next handler.

        Generate a unique request ID and attach it to the request state,
        then pass control to the next middleware or route handler.

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
            Final HTTP response object from the next handler.
        """
        # Attach a unique request ID to request state for downstream use
        request.state.unique_id = secrets.token_hex(16)

        # Delegate to the next middleware or route handler
        return await call_next()
