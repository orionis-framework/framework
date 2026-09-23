from typing import TYPE_CHECKING
from orionis.failure.contracts.catch import ICatch
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

# Successful responses eligible to become the previous page.
_SUCCESS_MIN: int = 200
_SUCCESS_MAX: int = 300

class StartSessionMiddleware(BaseMiddleware):

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("_catch", "_manager")

    def __init__(self, manager: SessionManager, catch: ICatch) -> None:
        """
        Initialise the middleware with the given session manager.

        Parameters
        ----------
        manager : SessionManager
            Session manager used for the start / save cycle.
        catch : ICatch
            Framework exception handler producing responses before persistence.

        Returns
        -------
        None
        """
        self._manager = manager
        self._catch = catch

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

        try:
            response = await self.__response(request, call_next)
            flash_data = response.getFlashData()
            if flash_data:
                apply_flash(session, flash_data)
            self.__storeCurrentUrl(request, response, session)
            await self._manager.save(response, session)
            return response
        except BaseException:
            await self._manager.abort(session)
            raise

    async def __response(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """Render failures while the session is still available for persistence.

        Parameters
        ----------
        request : Request
            Incoming request.
        call_next : Callable[[], Awaitable[Response]]
            Remaining middleware and controller pipeline.

        Returns
        -------
        Response
            Normal response or the framework's exception response.
        """
        try:
            return await call_next()
        except Exception as exc:  # noqa: BLE001
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

        # Keep the last successful page across redirects and failed requests.
        status = response.getStatusCode()
        if not _SUCCESS_MIN <= status < _SUCCESS_MAX:
            return

        session.setPreviousUrl(request.url)
