from types import SimpleNamespace
from orionis.http.layer.web.csrf_token import CSRFTokenMiddleware
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.payload.estructures.headers import Headers
from orionis.http.responses import Response
from orionis.session.session import Session
from orionis.test import TestCase

class _Request:
    """Expose request metadata and count body access during CSRF checks."""

    def __init__(self, method: str, headers: list[tuple[str, str]]) -> None:
        """Create a request with a concrete session and an existing CSRF token.

        Parameters
        ----------
        method : str
            Value supplied for ``method``.
        headers : list[tuple[str, str]]
            Value supplied for ``headers``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.method = method
        self.scheme = "https"
        self.headers = Headers(headers)
        self.state = SimpleNamespace(session=Session(data={"_csrf_token": "token"}))
        self.bodyReads = 0

    async def data(self) -> dict[str, object]:
        """Count an asynchronous body access and return an empty form.

        Returns
        -------
        dict[str, object]
            Value produced by the helper.
        """
        self.bodyReads += 1
        return {}

class _Terminal:
    """Count middleware continuation calls and return a concrete response."""

    def __init__(self) -> None:
        """Initialize the awaited-call counter and outgoing response.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.calls = 0
        self.response = Response()

    async def __call__(self) -> Response:
        """Record the awaited continuation and return its response.

        Returns
        -------
        Response
            Value produced by the helper.
        """
        self.calls += 1
        return self.response

class TestCSRFLifecycle(TestCase):
    """Keep token generation and validation consistent for every request method."""

    async def testSafeRequestPublishesTokenAndCookieWithoutReadingBody(self) -> None:
        """Expose the existing session token and issue the HTTPS XSRF cookie.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        request = _Request("GET", [])
        terminal = _Terminal()
        response = await CSRFTokenMiddleware({"xsrf_cookie": True}).handle(
            request, terminal,
        )
        self.assertEqual(request.state.csrf_token, "token")
        self.assertEqual(request.bodyReads, 0)
        self.assertEqual(terminal.calls, 1)
        self.assertIs(response, terminal.response)
        self.assertIn("XSRF-TOKEN=token", response.getHeader("set-cookie")[0])
        self.assertIn("Secure", response.getHeader("set-cookie")[0])

    async def testUnsafeRequestUsesHeaderTokenBeforeReadingBody(self) -> None:
        """Accept matching headers and reject mismatches before calling the handler.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        request = _Request("POST", [("x-csrf-token", "token")])
        terminal = _Terminal()
        middleware = CSRFTokenMiddleware({})
        self.assertIs(await middleware.handle(request, terminal), terminal.response)
        self.assertEqual(request.bodyReads, 0)
        self.assertEqual(terminal.calls, 1)
        request.headers = Headers([("x-csrf-token", "incorrect")])
        with self.assertRaises(CSRFTokenMismatchException):
            await middleware.handle(request, terminal)
        self.assertEqual(terminal.calls, 1)
        self.assertEqual(request.bodyReads, 0)
