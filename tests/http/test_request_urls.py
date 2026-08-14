from typing import Any
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.body import BodyStream
from orionis.http.payload.estructures.headers import Headers
from orionis.http.request import Request
from orionis.test import TestCase

class _FakeRSGIAdapter:
    """Adapter stub exposing the dictionary view of a Granian RSGI scope."""

    def __init__(
        self,
        scope: dict[str, Any],
        raw_headers: list[tuple[str, str]],
    ) -> None:
        """
        Store the scope view and the raw header pairs.

        Parameters
        ----------
        scope : dict[str, Any]
            Dictionary view of the RSGI scope.
        raw_headers : list[tuple[str, str]]
            Header name/value pairs for this request.
        """
        self._scope = scope
        self._headers = Headers(raw_headers)

    def getScope(self) -> dict[str, Any]:
        """
        Return the scope dictionary.

        Returns
        -------
        dict[str, Any]
            Scope view consumed by the request.
        """
        return self._scope

    def headers(self) -> Headers:
        """
        Return the parsed headers.

        Returns
        -------
        Headers
            Request headers.
        """
        return self._headers

def _makeRSGIRequest(
    host: str | None = "orionis.test",
    query: str = "",
) -> Request:
    """
    Build a request backed by an RSGI scope.

    Parameters
    ----------
    host : str | None, optional
        Value of the ``Host`` header; ``None`` omits the header.
    query : str, optional
        Raw query string.

    Returns
    -------
    Request
        Request instance using the RSGI interface.
    """
    scope: dict[str, Any] = {
        "scheme": "http",
        "method": "GET",
        "path": "/users/create",
        "query_string": query,
        "server": "127.0.0.1:8000",
        "client": "127.0.0.1:51234",
        "http_version": "1.1",
    }
    raw_headers: list[tuple[str, str]] = []
    if host is not None:
        raw_headers.append(("host", host))

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        interface=Interface.RSGI,
        adapter=_FakeRSGIAdapter(scope, raw_headers),
        body_stream=BodyStream(
            interface=Interface.RSGI,
            receive_or_protocol=receive,
        ),
        params={},
    )

class TestRSGIRequestUrls(TestCase):

    def testUrlUsesHostHeader(self) -> None:
        """
        Build the URL from the host the client actually requested.

        Validates that redirects stay on the same origin, so session
        cookies keep travelling with the request.
        """
        request = _makeRSGIRequest(host="orionis.test:8000")
        self.assertEqual(request.url, "http://orionis.test:8000/users/create")

    def testUrlIncludesQueryString(self) -> None:
        """
        Append the query string to the built URL.

        Validates that redirecting back preserves the current filters.
        """
        request = _makeRSGIRequest(query="page=2")
        self.assertEqual(request.url, "http://orionis.test/users/create?page=2")

    def testUrlFallsBackToServerWithoutHostHeader(self) -> None:
        """
        Fall back to the bound address when no Host header is sent.

        Validates that HTTP/1.0 style requests still produce a URL.
        """
        request = _makeRSGIRequest(host=None)
        self.assertEqual(request.url, "http://127.0.0.1:8000/users/create")

    def testBaseUrlUsesHostHeader(self) -> None:
        """
        Build the base URL from the host the client actually requested.

        Validates the origin used to decide whether a referrer is local.
        """
        request = _makeRSGIRequest(host="orionis.test:8000")
        self.assertEqual(request.baseUrl, "http://orionis.test:8000")

    def testBaseUrlFallsBackToServerWithoutHostHeader(self) -> None:
        """
        Fall back to the bound address for the base URL.

        Validates the behaviour preserved for clients without a Host header.
        """
        request = _makeRSGIRequest(host=None)
        self.assertEqual(request.baseUrl, "http://127.0.0.1:8000")
