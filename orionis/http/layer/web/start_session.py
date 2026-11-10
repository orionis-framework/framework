"""Open request sessions and persist their response-side changes."""

from typing import TYPE_CHECKING
from orionis.console.debug.dumper import HttpDump
from orionis.failure.contracts.catch import ICatch
from orionis.failure.runtime import capture
from orionis.http.middleware import BaseMiddleware
from orionis.session.flash import apply_flash
from orionis.session.manager import SessionManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from orionis.http.request import Request
    from orionis.http.responses import Response
    from orionis.session.contracts.session import ISession

# Only plain navigations are worth remembering as the "previous page".
_NAVIGATION_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})
"""Only plain navigations are worth remembering as the "previous page"."""

# Successful responses eligible to become the previous page.
_SUCCESS_MIN: int = 200
"""Successful responses eligible to become the previous page."""
_SUCCESS_MAX: int = 300
"""Success max value used by ``start_session``."""

class StartSessionMiddleware(BaseMiddleware):

    # ruff: noqa: TC001, BLE001
    """Open request sessions and persist their response-side changes."""

    __slots__ = ("_catch", "_manager", "_track_previous_url")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, manager: SessionManager, catch: ICatch) -> None:
        """
        Initialise the middleware with the given session manager.

        Parameters
        ----------
        manager : orionis.session.manager.SessionManager
            Session manager used for the start / save cycle.
        catch : orionis.failure.contracts.ICatch
            Framework exception handler producing responses before persistence.

        Returns
        -------
        None
            Initialise the middleware with the given session manager.
        """
        self._manager = manager
        """Session manager used for the start / save cycle."""
        self._catch = catch
        """Framework exception handler producing responses before persistence."""
        self._track_previous_url = manager.tracksPreviousUrl
        """Track previous url obtained from ``manager.tracksPreviousUrl``."""

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """
        Process the request through the session lifecycle.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming HTTP request.
        call_next : Callable[[], Awaitable[Response]]
            No-arg async callable that advances to the next middleware
            or final route handler.

        Returns
        -------
        orionis.http.Response
            The outgoing HTTP response, optionally augmented with a
            ``Set-Cookie`` header when the session was used.
        """
        # Restore or lazily create the session; attach it to request state
        # so handlers can reach it via request.state.session.
        session = await self._manager.start(request)
        request.state.session = session

        try:
            response = await self.__response(request, call_next)
            flash_data = response.getFlashData()
            if flash_data:
                apply_flash(session, flash_data)
            if self._track_previous_url:
                self.__storeCurrentUrl(request, response, session)
            await self._manager.save(response, session)
            return response
        except BaseException as error:
            if isinstance(error, Exception) and not isinstance(error, HttpDump):
                await capture(error, flow="http", phase="session")
            try:
                await self._manager.abort(session)
            except Exception as cleanup_error:
                await capture(cleanup_error, flow="http", phase="session.cleanup")
                raise
            raise

    async def __response(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """
        Render failures while the session is still available for persistence.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming request.
        call_next : Callable[[], Awaitable[Response]]
            Remaining middleware and controller pipeline.

        Returns
        -------
        orionis.http.Response
            Normal response or the framework's exception response.

        Raises
        ------
        orionis.console.debug.dumper.HttpDump
            If a dump must propagate to the HTTP kernel after session cleanup.
        """
        try:
            return await call_next()
        except HttpDump:
            raise
        except Exception as exc:
            return await self._catch.exception(exc, request)

    @staticmethod
    def __storeCurrentUrl(
        request: Request,
        response: Response,
        session: ISession,
    ) -> None:
        """
        Record the current URL as the page to redirect back to.

        Only GET/HEAD responses with status 200-299 are stored, excluding
        AJAX and requests that want JSON. Other statuses, background calls
        and form submissions never overwrite the previous page.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming HTTP request.
        response : orionis.http.Response
            Outgoing HTTP response.
        session : orionis.session.contracts.ISession
            Active session for this request.

        Returns
        -------
        None
            Record the current URL as the page to redirect back to.
        """
        if request.method not in _NAVIGATION_METHODS:
            return
        if request.isAjax() or request.wantsJson():
            return

        # Keep the last successful page across redirects and failed requests.
        status = response.getStatusCode()
        if not _SUCCESS_MIN <= status < _SUCCESS_MAX:
            return

        session.setPreviousUrl(request.url)
