from __future__ import annotations
from http.cookies import SimpleCookie
from pathlib import Path
from typing import TYPE_CHECKING
from orionis.http.layer.web.csrf_token import CSRFTokenMiddleware
from orionis.http.layer.web.start_session import StartSessionMiddleware
from orionis.http.responses import Response
from orionis.http.validation import previous_url
from orionis.session.manager import SessionManager
from orionis.test import TestCase
from tests.http.test_request import make_asgi_request

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from orionis.http.request import Request

_COOKIE_NAME = "test_session"
_PREVIOUS_URL = "http://orionis.test/last-good"
_CSRF_KEY = "_csrf_token"

class _SessionApplication:
    """Provide deterministic memory-session configuration and scoped binding."""

    def __init__(self, overrides: dict[str, object] | None = None) -> None:
        """Store the base path and explicit session options.

        Parameters
        ----------
        overrides : dict[str, object] or None, optional
            Session settings replacing the defaults.

        Returns
        -------
        None
            The memory driver's configuration is retained for this test.
        """
        self.basePath = Path()
        self._overrides = overrides or {}

    def config(self, key: str, default: object = None) -> object:
        """Return explicit session settings without reading environment defaults.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.
        default : object
            Value supplied for ``default``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        if key != "session":
            return default
        return {
            "driver": "memory",
            "lifetime": 120,
            "expire_on_close": False,
            "files": "unused",
            "connection": None,
            "table": "sessions",
            "cache": None,
            "cookie": _COOKIE_NAME,
            "path": "/",
            "domain": None,
            "secure": False,
            "http_only": True,
            "same_site": "lax",
            "partitioned": False,
            **self._overrides,
        }

    def instance(self, _contract: type, _instance: object) -> bool:
        """Accept the session binding used by the real manager.

        Parameters
        ----------
        _contract : type
            Value supplied for ``_contract``.
        _instance : object
            Value supplied for ``_instance``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

class _RecordingCatch:
    """Record downstream failures and render a concrete error response."""

    def __init__(self) -> None:
        """Initialize the recorded exception list.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.handled: list[Exception] = []

    async def exception(self, error: Exception, _request: Request) -> Response:
        """Keep the exception and return the response persisted by middleware.

        Parameters
        ----------
        error : Exception
            Value supplied for ``error``.
        _request : Request
            Value supplied for ``_request``.

        Returns
        -------
        Response
            Value produced by the helper.
        """
        self.handled.append(error)
        return Response(status_code=500)

class _Terminal:
    """Supply a concrete response or a requested controller failure."""

    def __init__(
        self, status_code: int = 200, error: Exception | None = None,
    ) -> None:
        """Store the response and optional exception for the awaited handler.

        Parameters
        ----------
        status_code : int
            Value supplied for ``status_code``.
        error : Exception | None
            Value supplied for ``error``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.response = Response(status_code=status_code)
        self.error = error

    async def __call__(self) -> Response:
        """Return the response or raise the supplied controller exception.

        Returns
        -------
        Response
            Value produced by the helper.

        Raises
        ------
        Exception
            The failure supplied by the test, when present.
        """
        if self.error is not None:
            raise self.error
        return self.response

def _make_request(
    session_id: str | None = None,
    *,
    method: str = "GET",
    path: str = "/next-page",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    """Build a real HTTP request carrying an optional persisted session cookie.

    Parameters
    ----------
    session_id : str | None
        Value supplied for ``session_id``.
    method : str
        Value supplied for ``method``.
    path : str
        Value supplied for ``path``.
    headers : list[tuple[bytes, bytes]] | None
        Value supplied for ``headers``.

    Returns
    -------
    Request
        Value produced by the helper.
    """
    request_headers = list(headers or [])
    if session_id is not None:
        request_headers.append((
            b"cookie", f"{_COOKIE_NAME}={session_id}".encode(),
        ))
    return make_asgi_request(
        headers=request_headers,
        scope_overrides={"method": method, "path": path},
    )

def _session_id(response: Response) -> str:
    """Extract the identifier emitted by the manager's real Set-Cookie header.

    Parameters
    ----------
    response : Response
        Value supplied for ``response``.

    Returns
    -------
    str
        Value produced by the helper.
    """
    cookies = SimpleCookie()
    for value in response.getHeader("set-cookie") or []:
        cookies.load(value)
    return cookies[_COOKIE_NAME].value

def _make_middleware(**overrides: object) -> tuple[
    SessionManager, StartSessionMiddleware, _RecordingCatch,
]:
    """Wire a real manager and its memory store into the public middleware.

    Parameters
    ----------
    **overrides : object
        Session options replacing the default test configuration.

    Returns
    -------
    tuple[SessionManager, StartSessionMiddleware, _RecordingCatch]
        The manager, middleware and exception recorder used by a test.
    """
    # The memory driver never reads its cache-manager collaborator.
    manager = SessionManager(_SessionApplication(overrides), None)
    catch = _RecordingCatch()
    return manager, StartSessionMiddleware(manager, catch), catch

async def _seed_navigation(middleware: StartSessionMiddleware) -> str:
    """Persist the original successful navigation through the public pipeline.

    Parameters
    ----------
    middleware : StartSessionMiddleware
        Value supplied for ``middleware``.

    Returns
    -------
    str
        Value produced by the helper.
    """
    response = await middleware.handle(
        _make_request(path="/last-good"), _Terminal(),
    )
    return _session_id(response)

async def _run_csrf_pipeline(
    session_middleware: StartSessionMiddleware,
    csrf_middleware: CSRFTokenMiddleware,
    request: Request,
    terminal: Callable[[], Awaitable[Response]],
) -> Response:
    """Execute the real session and CSRF middleware in their production order.

    Parameters
    ----------
    session_middleware : StartSessionMiddleware
        Value supplied for ``session_middleware``.
    csrf_middleware : CSRFTokenMiddleware
        Value supplied for ``csrf_middleware``.
    request : Request
        Value supplied for ``request``.
    terminal : Callable[[], Awaitable[Response]]
        Value supplied for ``terminal``.

    Returns
    -------
    Response
        Value produced by the helper.
    """
    async def next_middleware() -> Response:
        """Advance from the session middleware into CSRF validation.

        Returns
        -------
        Response
            Value produced by the helper.
        """
        return await csrf_middleware.handle(request, terminal)

    return await session_middleware.handle(request, next_middleware)

class TestSessionPersistence(TestCase):
    """Verify previous-page and CSRF behavior across stored request cycles."""

    async def _assertPreviousUrl(
        self, manager: SessionManager, response: Response, expected: str,
    ) -> None:
        """Restore the saved session and inspect validation's redirect target.

        Parameters
        ----------
        manager : SessionManager
            Value supplied for ``manager``.
        response : Response
            Value supplied for ``response``.
        expected : str
            Value supplied for ``expected``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        request = _make_request(_session_id(response), method="POST", path="/submit")
        request.state.session = await manager.start(request)
        self.assertEqual(request.state.session.getPreviousUrl(), expected)
        self.assertEqual(previous_url(request), expected)

    async def testSuccessfulNavigationsPersistTheirUrl(self) -> None:
        """Remember GET and HEAD pages throughout the complete 2xx interval.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        manager, middleware, catch = _make_middleware()
        session_id = await _seed_navigation(middleware)
        for method in ("GET", "HEAD"):
            for status in (200, 204, 206, 299):
                request = _make_request(
                    session_id, method=method, path=f"/success/{method}/{status}",
                )
                terminal = _Terminal(status)
                response = await middleware.handle(request, terminal)
                self.assertIs(response, terminal.response)
                await self._assertPreviousUrl(manager, response, request.url)
        self.assertEqual(catch.handled, [])

    async def testDisabledTrackingLeavesAnonymousNavigationWithoutSession(self) -> None:
        """Keep successful public navigation lazy when previous-page tracking is off.

        Returns
        -------
        None
            No session identifier, backing record or cookie is created.
        """
        _, middleware, _ = _make_middleware(track_previous_url=False)
        request = _make_request()
        response = await middleware.handle(request, _Terminal())
        self.assertFalse(request.state.session.started)
        self.assertIsNone(request.state.session.id)
        self.assertIsNone(response.getHeader("set-cookie"))

    async def testDisabledTrackingPreservesExplicitPreviousUrl(self) -> None:
        """Retain the previously recorded URL when automatic tracking is disabled.

        Returns
        -------
        None
            Navigation does not overwrite a manually stored redirect target.
        """
        manager, middleware, _ = _make_middleware(track_previous_url=False)
        session = await manager.start(_make_request())
        session.setPreviousUrl(_PREVIOUS_URL)
        await manager.save(Response(), session)
        response = await middleware.handle(_make_request(session.id), _Terminal())
        await self._assertPreviousUrl(manager, response, _PREVIOUS_URL)

    async def testDisabledTrackingRetainsCsrfPersistence(self) -> None:
        """Persist CSRF state independently of previous-page tracking.

        Returns
        -------
        None
            CSRF tokens and cookies still survive a stored session round trip.
        """
        manager, middleware, _ = _make_middleware(track_previous_url=False)
        request = _make_request()
        response = await _run_csrf_pipeline(
            middleware, CSRFTokenMiddleware({}), request, _Terminal(),
        )
        restored = await manager.start(_make_request(_session_id(response)))
        self.assertEqual(restored.get(_CSRF_KEY), request.state.csrf_token)
        self.assertIsNone(restored.getPreviousUrl())

    async def testDisabledTrackingAllowsUnchangedSessionsToSkipRenewal(self) -> None:
        """Retain session reads while omitting writes and cookies within the interval.

        Returns
        -------
        None
            A public navigation can read an existing scalar session unchanged.
        """
        manager, middleware, _ = _make_middleware(
            track_previous_url=False, renewal_interval=60,
        )
        session = await manager.start(_make_request())
        session.put("user_id", 42)
        await manager.save(Response(), session)
        request = _make_request(session.id)
        response = await middleware.handle(request, _Terminal())
        self.assertEqual(request.state.session.get("user_id"), 42)
        self.assertFalse(request.state.session.dirty)
        self.assertIsNone(response.getHeader("set-cookie"))

    async def testOtherStatusesPreserveThePreviousSuccessfulPage(self) -> None:
        """Keep the stored page across informational, redirect and error statuses.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        manager, middleware, catch = _make_middleware()
        session_id = await _seed_navigation(middleware)
        for method in ("GET", "HEAD"):
            for status in (100, 199, 300, 302, 399, 400, 404, 499, 500, 599):
                request = _make_request(
                    session_id, method=method, path=f"/excluded/{method}/{status}",
                )
                response = await middleware.handle(request, _Terminal(status))
                self.assertEqual(response.getStatusCode(), status)
                await self._assertPreviousUrl(manager, response, _PREVIOUS_URL)
        self.assertEqual(catch.handled, [])

    async def testBackgroundAndOtherMethodsPreserveThePreviousPage(self) -> None:
        """Exclude successful submissions, AJAX calls and JSON negotiations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        manager, middleware, catch = _make_middleware()
        session_id = await _seed_navigation(middleware)
        cases = [
            (method, [])
            for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE")
        ]
        cases.extend(
            (method, [header])
            for method in ("GET", "HEAD")
            for header in (
                (b"x-requested-with", b"XMLHttpRequest"),
                (b"accept", b"application/json"),
            )
        )
        for method, headers in cases:
            response = await middleware.handle(
                _make_request(session_id, method=method, headers=headers), _Terminal(),
            )
            await self._assertPreviousUrl(manager, response, _PREVIOUS_URL)
        self.assertEqual(catch.handled, [])

    async def testHandledControllerFailurePreservesThePreviousPage(self) -> None:
        """Save the unchanged URL after the exception handler renders a 500.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        manager, middleware, catch = _make_middleware()
        session_id = await _seed_navigation(middleware)
        failure = RuntimeError("Controller failed")
        response = await middleware.handle(
            _make_request(session_id, path="/failed"), _Terminal(error=failure),
        )
        self.assertEqual(response.getStatusCode(), 500)
        self.assertEqual(catch.handled, [failure])
        await self._assertPreviousUrl(manager, response, _PREVIOUS_URL)

    async def testRegenerationPreservesCsrfAcrossPersistence(self) -> None:
        """Rotate the session identifier while retaining the token after restore.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        manager, middleware, catch = _make_middleware()
        csrf = CSRFTokenMiddleware({})
        first = _make_request()
        response = await _run_csrf_pipeline(middleware, csrf, first, _Terminal())
        original_id = _session_id(response)
        original_token = first.state.csrf_token
        self.assertTrue(original_token)

        rotating = _make_request(original_id)

        async def regenerate() -> Response:
            """Request an ID rotation without explicitly changing the CSRF value.

            Returns
            -------
            Response
                Value produced by the helper.
            """
            rotating.state.session.regenerate()
            return Response()

        response = await _run_csrf_pipeline(middleware, csrf, rotating, regenerate)
        rotated_id = _session_id(response)
        self.assertNotEqual(rotated_id, original_id)
        self.assertEqual(rotating.state.csrf_token, original_token)
        self.assertEqual(rotating.state.session.get(_CSRF_KEY), original_token)
        self.assertFalse(rotating.state.session.wantsRegenerate)

        restored = _make_request(rotated_id)
        response = await _run_csrf_pipeline(middleware, csrf, restored, _Terminal())
        self.assertEqual(_session_id(response), rotated_id)
        self.assertEqual(restored.state.csrf_token, original_token)
        self.assertEqual(restored.state.session.get(_CSRF_KEY), original_token)
        stale = await manager.start(_make_request(original_id))
        self.assertFalse(stale.started)
        self.assertIsNone(stale.get(_CSRF_KEY))
        self.assertEqual(catch.handled, [])
