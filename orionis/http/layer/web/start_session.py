from typing import TYPE_CHECKING
from orionis.http.middleware import BaseMiddleware
from orionis.session.flash import apply_flash
from orionis.session.manager import SessionManager
from orionis.support.facades.session import Session

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from orionis.http.request import Request
    from orionis.http.response import Response
    from orionis.session.contracts.session import ISession

# Only plain navigations are worth remembering as the "previous page".
_NAVIGATION_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})

# Status range that marks a response as a redirection.
_REDIRECT_MIN: int = 300
_REDIRECT_MAX: int = 400

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
            apply_flash(session, flash_data)

        # Remember this page so a later failed submission can redirect back.
        self.__storeCurrentUrl(request, response, session)

        # Persist the session and set the cookie only when it was used.
        await self._manager.save(response, session)

        # Return the response to the client.
        return response

    @staticmethod
    def __storeCurrentUrl(
        request: Request,
        response: Response,
        session: ISession,
    ) -> None:
        """
        Record the current URL as the page to redirect back to.

        Only successful, non-AJAX navigations are stored, so redirects,
        background calls and form submissions never overwrite it.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        response : Response
            Outgoing HTTP response.
        session : ISession
            Active session for this request.

        Returns
        -------
        None
        """
        if request.method not in _NAVIGATION_METHODS:
            return
        if request.isAjax() or request.wantsJson():
            return

        # Redirections are transient; keep the page the user actually saw.
        status = response.getStatusCode()
        if _REDIRECT_MIN <= status < _REDIRECT_MAX:
            return

        session.setPreviousUrl(request.url)
