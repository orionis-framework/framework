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

    def __init__(self) -> None:
        """Provide the base path required while selecting the memory driver."""
        self.basePath = Path()

    def config(self, key: str, default: object = None) -> object:
        """Return explicit session settings without reading environment defaults."""
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
        }

    def instance(self, _contract: type, _instance: object) -> bool:
        """Accept the session binding used by the real manager."""
        return True


class _RecordingCatch:
    """Record downstream failures and render a concrete error response."""

    def __init__(self) -> None:
        """Initialize the recorded exception list."""
        self.handled: list[Exception] = []

    async def exception(self, error: Exception, _request: Request) -> Response:
        """Keep the exception and return the response persisted by middleware."""
        self.handled.append(error)
        return Response(status_code=500)


class _Terminal:
    """Supply a concrete response or a requested controller failure."""

    def __init__(
        self, status_code: int = 200, error: Exception | None = None,
    ) -> None:
        """Store the response and optional exception for the awaited handler."""
        self.response = Response(status_code=status_code)
        self.error = error

    async def __call__(self) -> Response:
        """Return the response or raise the supplied controller exception.

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
    """Build a real HTTP request carrying an optional persisted session cookie."""
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
    """Extract the identifier emitted by the manager's real Set-Cookie header."""
    cookies = SimpleCookie()
    for value in response.getHeader("set-cookie") or []:
        cookies.load(value)
    return cookies[_COOKIE_NAME].value


def _make_middleware() -> tuple[
    SessionManager, StartSessionMiddleware, _RecordingCatch,
]:
    """Wire a real manager and its memory store into the public middleware."""
    # The memory driver never reads its cache-manager collaborator.
    manager = SessionManager(_SessionApplication(), None)
    catch = _RecordingCatch()
    return manager, StartSessionMiddleware(manager, catch), catch


async def _seed_navigation(middleware: StartSessionMiddleware) -> str:
    """Persist the original successful navigation through the public pipeline."""
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
    """Execute the real session and CSRF middleware in their production order."""
    async def next_middleware() -> Response:
        """Advance from the session middleware into CSRF validation."""
        return await csrf_middleware.handle(request, terminal)

    return await session_middleware.handle(request, next_middleware)


class TestSessionPersistence(TestCase):
    """Verify previous-page and CSRF behavior across stored request cycles."""

    async def _assertPreviousUrl(
        self, manager: SessionManager, response: Response, expected: str,
    ) -> None:
        """Restore the saved session and inspect validation's redirect target."""
        request = _make_request(_session_id(response), method="POST", path="/submit")
        request.state.session = await manager.start(request)
        self.assertEqual(request.state.session.getPreviousUrl(), expected)
        self.assertEqual(previous_url(request), expected)

    async def testSuccessfulNavigationsPersistTheirUrl(self) -> None:
        """Remember GET and HEAD pages throughout the complete 2xx interval."""
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

    async def testOtherStatusesPreserveThePreviousSuccessfulPage(self) -> None:
        """Keep the stored page across informational, redirect and error statuses."""
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
        """Exclude successful submissions, AJAX calls and JSON negotiations."""
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
        """Save the unchanged URL after the exception handler renders a 500."""
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
        """Rotate the session identifier while retaining the token after restore."""
        manager, middleware, catch = _make_middleware()
        csrf = CSRFTokenMiddleware({})
        first = _make_request()
        response = await _run_csrf_pipeline(middleware, csrf, first, _Terminal())
        original_id = _session_id(response)
        original_token = first.state.csrf_token
        self.assertTrue(original_token)

        rotating = _make_request(original_id)

        async def regenerate() -> Response:
            """Request an ID rotation without explicitly changing the CSRF value."""
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
