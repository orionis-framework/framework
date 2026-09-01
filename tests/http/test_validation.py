from typing import Any
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.body import BodyStream
from orionis.http.request import Request
from orionis.http.responses import JSONResponse, RedirectResponse
from orionis.http.validation import previous_url, validation_response
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exceptions.validation import ValidationException
from orionis.session.flash import ERRORS_KEY, OLD_INPUT_KEY
from orionis.session.session import Session
from orionis.test import TestCase

class _FakeDefaultResponses:
    """Minimal stand-in for the default response factory."""

    __slots__ = ("expects_json",)

    def __init__(self) -> None:
        """Initialise the recorder of the negotiated payload format."""
        self.expects_json: bool = False

    def error(
        self,
        status_code: int,
        content: dict,
        *,
        expects_json: bool,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        """
        Return a JSON response mirroring the real factory contract.

        Parameters
        ----------
        status_code : int
            HTTP status code to report.
        content : dict
            Error payload.
        expects_json : bool
            Whether the caller asked for a JSON payload.
        headers : dict[str, str] | None, optional
            Extra headers.

        Returns
        -------
        JSONResponse
            Response carrying the given payload.
        """
        self.expects_json = expects_json
        return JSONResponse(content=content, status_code=status_code, headers=headers)

def _makeRequest(
    body: bytes = b"",
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    """
    Build a real POST request backed by an ASGI scope.

    Parameters
    ----------
    body : bytes, optional
        Raw urlencoded request body.
    extra_headers : list[tuple[bytes, bytes]] | None, optional
        Additional raw headers appended to the scope.

    Returns
    -------
    Request
        Fully constructed request instance.
    """
    headers: list[tuple[bytes, bytes]] = [
        (b"host", b"orionis.test"),
        (b"content-type", b"application/x-www-form-urlencoded"),
    ]
    if extra_headers:
        headers.extend(extra_headers)

    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/login",
        "raw_path": b"/login",
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("orionis.test", 80),
        "client": ("127.0.0.1", 51234),
        "http_version": "1.1",
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        interface=Interface.ASGI,
        adapter=ASGITransportAdapter(scope),
        body_stream=BodyStream(
            interface=Interface.ASGI,
            receive_or_protocol=receive,
        ),
        params={},
    )

def _makeException() -> ValidationException:
    """
    Build a validation exception with two offending fields.

    Returns
    -------
    ValidationException
        Exception carrying failures for ``email`` and ``password``.
    """
    return ValidationException([
        ValidationFailure(field="email", rule="pattern", message="Invalid email."),
        ValidationFailure(
            field="password",
            rule="min_length",
            message="Password too short.",
        ),
    ])

class TestValidationResponseForJson(TestCase):

    async def testJsonClientGets422(self) -> None:
        """
        Return a 422 response when the client accepts JSON.

        Validates that API-style clients receive the structured payload
        instead of a redirect.
        """
        request = _makeRequest(
            extra_headers=[(b"accept", b"application/json")],
        )
        response = await validation_response(
            _makeException(), request, _FakeDefaultResponses(),
        )
        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.getStatusCode(), 422)

    async def testAjaxClientGets422(self) -> None:
        """
        Return a 422 response for XMLHttpRequest submissions.

        Validates that AJAX form posts are answered with JSON even when the
        Accept header prefers HTML.
        """
        request = _makeRequest(
            extra_headers=[
                (b"accept", b"text/html"),
                (b"x-requested-with", b"XMLHttpRequest"),
            ],
        )
        response = await validation_response(
            _makeException(), request, _FakeDefaultResponses(),
        )
        self.assertIsInstance(response, JSONResponse)

    async def testJsonPayloadCarriesFieldErrors(self) -> None:
        """
        Expose every field error in the JSON payload.

        Validates the ``message`` plus ``errors`` contract consumed by
        front-end clients.
        """
        request = _makeRequest(
            extra_headers=[(b"accept", b"application/json")],
        )
        responses = _FakeDefaultResponses()
        await validation_response(_makeException(), request, responses)
        self.assertTrue(responses.expects_json)

class TestValidationResponseForWeb(TestCase):

    async def testBrowserIsRedirectedBack(self) -> None:
        """
        Redirect the browser back to the submitted form.

        Validates that an HTML client receives a 302 pointing at the
        referring page.
        """
        request = _makeRequest(
            extra_headers=[
                (b"accept", b"text/html"),
                (b"referer", b"http://orionis.test/login"),
            ],
        )
        response = await validation_response(
            _makeException(), request, _FakeDefaultResponses(),
        )
        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.getStatusCode(), 302)
        self.assertEqual(
            response.getHeader("location"),
            ["http://orionis.test/login"],
        )

    async def testErrorsAreFlashed(self) -> None:
        """
        Queue every field error in the response flash bag.

        Validates that the errors bag reaches the session middleware with
        one entry per offending field.
        """
        request = _makeRequest(extra_headers=[(b"accept", b"text/html")])
        response = await validation_response(
            _makeException(), request, _FakeDefaultResponses(),
        )
        flash = response.getFlashData()
        self.assertEqual(
            flash[ERRORS_KEY],
            {
                "email": ["Invalid email."],
                "password": ["Password too short."],
            },
        )

    async def testSubmittedInputIsFlashedWithoutCredentials(self) -> None:
        """
        Repopulate the form without leaking credential fields.

        Validates that the submitted payload is flashed as old input and
        that the password is stripped from it.
        """
        request = _makeRequest(
            body=b"email=user%40mail.test&password=secret",
            extra_headers=[(b"accept", b"text/html")],
        )
        response = await validation_response(
            _makeException(), request, _FakeDefaultResponses(),
        )
        old_input = response.getFlashData()[OLD_INPUT_KEY]
        self.assertEqual(old_input, {"email": "user@mail.test"})

    async def testUnparsableBodyStillRedirects(self) -> None:
        """
        Redirect even when the submitted body cannot be parsed.

        Validates that an unsupported media type degrades to a redirect
        carrying the errors, without old input.
        """
        request = _makeRequest(
            body=b"<xml/>",
            extra_headers=[
                (b"accept", b"text/html"),
                (b"content-type", b"application/octet-stream"),
            ],
        )
        response = await validation_response(
            _makeException(), request, _FakeDefaultResponses(),
        )
        self.assertIsInstance(response, RedirectResponse)
        self.assertNotIn(OLD_INPUT_KEY, response.getFlashData())

class TestPreviousUrl(TestCase):

    def testSessionPreviousUrlWins(self) -> None:
        """
        Prefer the page recorded by the session middleware.

        Validates that the last visited page takes precedence over the
        referrer, which browsers may omit.
        """
        request = _makeRequest(
            extra_headers=[(b"referer", b"http://orionis.test/login")],
        )
        session = Session()
        session.setPreviousUrl("http://orionis.test/users/create")
        request.state.session = session
        self.assertEqual(previous_url(request), "http://orionis.test/users/create")

    def testRefererIsUsedWhenSessionHasNoPreviousUrl(self) -> None:
        """
        Fall back to the referrer for a session without a recorded page.

        Validates the second step of the resolution chain.
        """
        request = _makeRequest(
            extra_headers=[(b"referer", b"http://orionis.test/register")],
        )
        request.state.session = Session()
        self.assertEqual(previous_url(request), "http://orionis.test/register")

    def testSameOriginRefererIsUsed(self) -> None:
        """
        Redirect back to a referrer belonging to this application.

        Validates that an absolute same-origin URL is preserved.
        """
        request = _makeRequest(
            extra_headers=[(b"referer", b"http://orionis.test/register")],
        )
        self.assertEqual(previous_url(request), "http://orionis.test/register")

    def testRelativeRefererIsUsed(self) -> None:
        """
        Accept a relative referrer path.

        Validates that a path-only referrer is treated as same-origin.
        """
        request = _makeRequest(extra_headers=[(b"referer", b"/register")])
        self.assertEqual(previous_url(request), "/register")

    def testExternalRefererFallsBackToCurrentUrl(self) -> None:
        """
        Ignore a referrer pointing to another origin.

        Validates that the redirect target cannot be controlled by an
        external site, preventing open redirects.
        """
        request = _makeRequest(
            extra_headers=[(b"referer", b"http://evil.test/phish")],
        )
        self.assertEqual(previous_url(request), "http://orionis.test/login")

    def testProtocolRelativeRefererFallsBackToCurrentUrl(self) -> None:
        """
        Ignore a protocol-relative referrer.

        Validates that ``//evil.test`` is not mistaken for a local path.
        """
        request = _makeRequest(
            extra_headers=[(b"referer", b"//evil.test/phish")],
        )
        self.assertEqual(previous_url(request), "http://orionis.test/login")

    def testMissingRefererFallsBackToCurrentUrl(self) -> None:
        """
        Redirect back to the submitted URL without a referrer.

        Validates that the form endpoint is used as the last resort instead
        of sending the user to the application root.
        """
        self.assertEqual(previous_url(_makeRequest()), "http://orionis.test/login")
