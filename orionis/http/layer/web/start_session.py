from typing import TYPE_CHECKING
from orionis.http.middleware import BaseMiddleware
from orionis.session.manager import SessionManager
from orionis.support.facades.session import Session

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from orionis.http.request import Request
    from orionis.http.response import Response

class StartSessionMiddleware(BaseMiddleware):

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("_manager",)

    def __init__(self, manager: SessionManager) -> None:
        """
        Initialise the middleware with the given session manager.

        Parameters
        ----------
        manager : SessionManager
            Session manager used for the start / save cycle.

        Returns
        -------
        None
        """
        self._manager = manager

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """
        Process the request through the session lifecycle.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        call_next : Callable[[], Awaitable[Response]]
            No-arg async callable that advances to the next middleware
            or final route handler.

        Returns
        -------
        Response
            The outgoing HTTP response, optionally augmented with a
            ``Set-Cookie`` header when the session was used.
        """
        # Restore or lazily create the session; attach it to request state
        # so handlers can reach it via request.state.session.
        session = await self._manager.start(request)
        request.state.session = session

        # Pin Session Facade.
        await Session.pin()

       # Advance through the rest of the middleware pipeline.
        response = await call_next()

        # Unpin Session Facade.
        Session.unpin()

        # Move data queued with ``Response.withFlash()`` into the flash bag.
        flash_data = response.getFlashData()
        if flash_data:
            for key, value in flash_data.items():
                session.flash(key, value)

        # Persist the session and set the cookie only when it was used.
        await self._manager.save(response, session)

        # Return the response to the client.
        return response
