from __future__ import annotations
from typing import TYPE_CHECKING, Any
from xml.etree.ElementTree import ParseError
from msgspec import msgpack
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.body import BodyStream
from orionis.http.payload.estructures.cookies import Cookies
from orionis.http.payload.estructures.headers import Headers
from orionis.http.payload.estructures.query_params import QueryParams
from orionis.http.payload.form_data import FormData
from orionis.http.payload.media_types import DEFAULT_MEDIA_TYPES, MediaTypeRegistry
from orionis.http.request import Request, UnsupportedMediaTypeException
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_BOUNDARY: str = "orionisboundary"
_CREDENTIAL_FIELD: str = "password"
_CSRF_VALUE: str = "abc123"


class _StubRSGIAdapter:
    """Adapter double exposing the dictionary view of a Granian RSGI scope."""

    __slots__ = ("_headers", "_scope")

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
            Header name and value pairs for this request.
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


def make_receive(body: bytes) -> Callable[[], Coroutine[Any, Any, dict[str, Any]]]:
    """
    Build an ASGI receive callable delivering a whole body at once.

    Parameters
    ----------
    body : bytes
        Raw request body.

    Returns
    -------
    Callable[[], Coroutine[Any, Any, dict[str, Any]]]
        Callable returning a single ``http.request`` message.
    """

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def make_asgi_request(  # noqa: PLR0913
    *,
    body: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
    scope_overrides: dict[str, Any] | None = None,
    remove: tuple[str, ...] = (),
    params: dict[str, Any] | None = None,
    registry: MediaTypeRegistry | None = None,
    interface: Interface | str = Interface.ASGI,
) -> Request:
    """
    Build a request backed by a real ASGI transport adapter.

    Parameters
    ----------
    body : bytes, optional
        Raw request body.
    headers : list[tuple[bytes, bytes]] | None, optional
        Raw header pairs added to the scope.
    scope_overrides : dict[str, Any] | None, optional
        Scope entries replacing the defaults.
    remove : tuple[str, ...], optional
        Scope keys deleted before building the adapter.
    params : dict[str, Any] | None, optional
        Path parameters extracted by the router.
    registry : MediaTypeRegistry | None, optional
        Media-type registry injected into the request.
    interface : Interface | str, optional
        Interface value handed to the request constructor.

    Returns
    -------
    Request
        Fully constructed request instance.
    """
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/users",
        "query_string": b"",
        "headers": list(headers or []),
        "scheme": "http",
        "server": ("orionis.test", 80),
        "client": ("127.0.0.1", 51234),
        "http_version": "1.1",
    }
    if scope_overrides:
        scope.update(scope_overrides)
    for key in remove:
        scope.pop(key, None)

    return Request(
        interface=interface,
        adapter=ASGITransportAdapter(scope),
        body_stream=BodyStream(
            interface=Interface.ASGI,
            receive_or_protocol=make_receive(body),
        ),
        registry=registry,
        params=params,
    )


def make_rsgi_request(
    *,
    host: str | None = "orionis.test",
    query: str = "",
    scope_overrides: dict[str, Any] | None = None,
) -> Request:
    """
    Build a request backed by an RSGI scope double.

    Parameters
    ----------
    host : str | None, optional
        Value of the ``Host`` header; ``None`` omits the header.
    query : str, optional
        Raw query string.
    scope_overrides : dict[str, Any] | None, optional
        Scope entries replacing the defaults.

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
        "client": "127.0.0.1",
        "http_version": "1.1",
    }
    if scope_overrides:
        scope.update(scope_overrides)

    raw_headers: list[tuple[str, str]] = []
    if host is not None:
        raw_headers.append(("host", host))

    return Request(
        interface=Interface.RSGI,
        adapter=_StubRSGIAdapter(scope, raw_headers),
        body_stream=BodyStream(
            interface=Interface.ASGI,
            receive_or_protocol=make_receive(b""),
        ),
        params={},
    )


def make_multipart_body(fields: list[tuple[str, str]]) -> bytes:
    """
    Build a multipart payload carrying only text fields.

    Parameters
    ----------
    fields : list[tuple[str, str]]
        Ordered field name and value pairs.

    Returns
    -------
    bytes
        Encoded ``multipart/form-data`` body.
    """
    parts: list[str] = []
    for name, value in fields:
        parts.append(f"--{_BOUNDARY}\r\n")
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
        parts.append(f"{value}\r\n")
    parts.append(f"--{_BOUNDARY}--\r\n")
    return "".join(parts).encode()


class TestRequestConstruction(TestCase):

    def testCoercesARawInterfaceValue(self) -> None:
        """
        Accept the textual form of the interface enumeration.

        Validates that transports handing over a raw string still produce
        a fully typed request.
        """
        request = make_asgi_request(interface="asgi")
        self.assertIs(request.interface, Interface.ASGI)

    def testKeepsAnAlreadyTypedInterface(self) -> None:
        """
        Reuse the enumeration member supplied by the caller.

        Validates the fast path taken by the kernel on every request.
        """
        request = make_asgi_request(interface=Interface.ASGI)
        self.assertIs(request.interface, Interface.ASGI)

    def testDefaultsToAnEmptyParameterMapping(self) -> None:
        """
        Start with no path parameters when the router supplies none.

        Validates that static routes never receive a shared mutable
        default.
        """
        self.assertEqual(make_asgi_request().routeParams(), {})

    def testExposesTheRawTransportScope(self) -> None:
        """
        Expose the untouched transport scope.

        Validates the escape hatch used by tracing and ASGI-aware
        extensions.
        """
        request = make_asgi_request()
        self.assertEqual(request.scope["type"], "http")

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep requests free of a per-instance dictionary.

        Validates the slot layout that keeps the request hot path cheap.
        """
        self.assertFalse(hasattr(make_asgi_request(), "__dict__"))


class TestRequestLine(TestCase):

    def testExposesTheHttpMethod(self) -> None:
        """
        Expose the HTTP method and cache it after the first read.

        Validates the value the router dispatches on.
        """
        request = make_asgi_request()
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.method, "POST")

    def testExposesTheScheme(self) -> None:
        """
        Expose the scheme declared by the transport.

        Validates the value used to build absolute URLs.
        """
        request = make_asgi_request(scope_overrides={"scheme": "https"})
        self.assertEqual(request.scheme, "https")
        self.assertEqual(request.scheme, "https")

    def testSchemeFallsBackToHttp(self) -> None:
        """
        Assume plain HTTP when the transport omits the scheme.

        Validates the default applied by minimal ASGI servers.
        """
        self.assertEqual(make_asgi_request(remove=("scheme",)).scheme, "http")

    def testExposesThePath(self) -> None:
        """
        Expose the request path and cache it after the first read.

        Validates the value matched against the route table.
        """
        request = make_asgi_request()
        self.assertEqual(request.path, "/users")
        self.assertEqual(request.path, "/users")

    def testPathFallsBackToRoot(self) -> None:
        """
        Assume the root path when the transport omits it.

        Validates the default applied by minimal ASGI servers.
        """
        self.assertEqual(make_asgi_request(remove=("path",)).path, "/")

    def testExposesTheHttpVersion(self) -> None:
        """
        Expose the negotiated HTTP version and cache it.

        Validates the value reported by the debug request printer.
        """
        request = make_asgi_request(scope_overrides={"http_version": "2"})
        self.assertEqual(request.httpVersion, "2")
        self.assertEqual(request.httpVersion, "2")

    def testHttpVersionFallsBackToOneDotOne(self) -> None:
        """
        Assume HTTP/1.1 when the transport omits the version.

        Validates the default applied by minimal ASGI servers.
        """
        request = make_asgi_request(remove=("http_version",))
        self.assertEqual(request.httpVersion, "1.1")


class TestAsgiRequestUrls(TestCase):

    def testUsesTheHostHeader(self) -> None:
        """
        Build the URL from the host the client actually requested.

        Validates that redirects stay on the same origin so session
        cookies keep travelling with the request.
        """
        request = make_asgi_request(headers=[(b"host", b"app.test:8000")])
        self.assertEqual(request.url, "http://app.test:8000/users")

    def testAppendsTheQueryString(self) -> None:
        """
        Append the decoded query string to the URL.

        Validates that redirecting back preserves the current filters.
        """
        request = make_asgi_request(
            headers=[(b"host", b"app.test")],
            scope_overrides={"query_string": b"page=2"},
        )
        self.assertEqual(request.url, "http://app.test/users?page=2")

    def testOmitsTheDefaultPortFromTheHost(self) -> None:
        """
        Drop the port when it matches the scheme default.

        Validates the canonical origin used for referrer comparison.
        """
        request = make_asgi_request(scope_overrides={"server": ("app.test", 80)})
        self.assertEqual(request.url, "http://app.test/users")

    def testKeepsANonDefaultPort(self) -> None:
        """
        Keep the port when it differs from the scheme default.

        Validates local development URLs such as ``:8000``.
        """
        request = make_asgi_request(scope_overrides={"server": ("app.test", 8000)})
        self.assertEqual(request.url, "http://app.test:8000/users")

    def testUsesTheSecureDefaultPort(self) -> None:
        """
        Drop port ``443`` for HTTPS requests.

        Validates the scheme-aware default-port table.
        """
        request = make_asgi_request(
            scope_overrides={"scheme": "https", "server": ("app.test", 443)},
        )
        self.assertEqual(request.url, "https://app.test/users")

    def testFallsBackToTheBarePathWithoutAHost(self) -> None:
        """
        Return a relative URL when neither host nor server is known.

        Validates that URL building never raises on a minimal scope.
        """
        request = make_asgi_request(remove=("server",))
        self.assertEqual(request.url, "/users")

    def testFallsBackToTheBarePathWithQuery(self) -> None:
        """
        Return a relative URL carrying the query string.

        Validates that filters survive even on a minimal scope.
        """
        request = make_asgi_request(
            remove=("server",),
            scope_overrides={"query_string": b"page=2"},
        )
        self.assertEqual(request.url, "/users?page=2")

    def testCachesTheBuiltUrl(self) -> None:
        """
        Build the URL once and reuse it afterwards.

        Validates the cache that keeps repeated reads free.
        """
        request = make_asgi_request()
        self.assertIs(request.url, request.url)

    def testBaseUrlUsesTheHostHeader(self) -> None:
        """
        Build the base URL from the requested host.

        Validates the origin used to decide whether a referrer is local.
        """
        request = make_asgi_request(headers=[(b"host", b"app.test:8000")])
        self.assertEqual(request.baseUrl, "http://app.test:8000")

    def testBaseUrlIncludesTheRootPath(self) -> None:
        """
        Append the mount point to the base URL.

        Validates applications served under a sub-path.
        """
        request = make_asgi_request(scope_overrides={"root_path": "/admin"})
        self.assertEqual(request.baseUrl, "http://orionis.test/admin")

    def testBaseUrlKeepsANonDefaultPort(self) -> None:
        """
        Keep a non-default port in the base URL.

        Validates local development origins.
        """
        request = make_asgi_request(scope_overrides={"server": ("app.test", 8080)})
        self.assertEqual(request.baseUrl, "http://app.test:8080")

    def testBaseUrlUsesTheSecureDefaultPort(self) -> None:
        """
        Drop port ``443`` from the HTTPS base URL.

        Validates the scheme-aware default-port table.
        """
        request = make_asgi_request(
            scope_overrides={"scheme": "https", "server": ("app.test", 443)},
        )
        self.assertEqual(request.baseUrl, "https://app.test")

    def testBaseUrlFallsBackToLocalhost(self) -> None:
        """
        Fall back to ``localhost`` when the origin is unknown.

        Validates that referrer checks still have a value to compare
        against.
        """
        request = make_asgi_request(remove=("server",))
        self.assertEqual(request.baseUrl, "http://localhost")

    def testCachesTheBuiltBaseUrl(self) -> None:
        """
        Build the base URL once and reuse it afterwards.

        Validates the cache that keeps repeated reads free.
        """
        request = make_asgi_request()
        self.assertIs(request.baseUrl, request.baseUrl)


class TestRsgiRequestUrls(TestCase):

    def testUrlUsesTheHostHeader(self) -> None:
        """
        Build the URL from the host the client actually requested.

        Validates parity with the ASGI transport, so redirects keep the
        session cookie.
        """
        request = make_rsgi_request(host="orionis.test:8000")
        self.assertEqual(request.url, "http://orionis.test:8000/users/create")

    def testUrlIncludesTheQueryString(self) -> None:
        """
        Append the query string to the built URL.

        Validates that redirecting back preserves the current filters.
        """
        request = make_rsgi_request(query="page=2")
        self.assertEqual(request.url, "http://orionis.test/users/create?page=2")

    def testUrlFallsBackToTheBoundAddress(self) -> None:
        """
        Fall back to the bound address when no host header is sent.

        Validates that HTTP/1.0 style requests still produce a URL.
        """
        request = make_rsgi_request(host=None)
        self.assertEqual(request.url, "http://127.0.0.1:8000/users/create")

    def testBaseUrlUsesTheHostHeader(self) -> None:
        """
        Build the base URL from the requested host.

        Validates the origin used to decide whether a referrer is local.
        """
        request = make_rsgi_request(host="orionis.test:8000")
        self.assertEqual(request.baseUrl, "http://orionis.test:8000")

    def testBaseUrlFallsBackToTheBoundAddress(self) -> None:
        """
        Fall back to the bound address for the base URL.

        Validates the behaviour preserved for clients without a host
        header.
        """
        request = make_rsgi_request(host=None)
        self.assertEqual(request.baseUrl, "http://127.0.0.1:8000")

    def testQueryParamsReadTheRawScopeValue(self) -> None:
        """
        Parse the query string carried as text by the RSGI scope.

        Validates the transport-specific branch of the parser.
        """
        request = make_rsgi_request(query="page=2&page=3")
        self.assertEqual(request.queryParams.getAll("page"), ["2", "3"])

    def testQueryParamsTolerateAMissingQueryString(self) -> None:
        """
        Treat a null query string as an empty one.

        Validates the guard protecting the RSGI branch.
        """
        request = make_rsgi_request(scope_overrides={"query_string": None})
        self.assertEqual(len(request.queryParams), 0)


class TestRequestStructures(TestCase):

    def testHeadersAreBuiltOnceAndCached(self) -> None:
        """
        Build the header index once per request.

        Validates the cache shared by every header-derived accessor.
        """
        request = make_asgi_request(headers=[(b"x-a", b"1")])
        self.assertIsInstance(request.headers, Headers)
        self.assertIs(request.headers, request.headers)

    def testQueryParamsAreDecodedAndCached(self) -> None:
        """
        Decode the ASGI query string and cache the result.

        Validates the parser used by controllers reading filters.
        """
        request = make_asgi_request(scope_overrides={"query_string": b"a=1&b=2"})
        self.assertIsInstance(request.queryParams, QueryParams)
        self.assertEqual(request.queryParams.get("a"), "1")
        self.assertIs(request.queryParams, request.queryParams)

    def testCookiesAreParsedAndCached(self) -> None:
        """
        Parse the cookie header once per request.

        Validates the accessor used by the session middleware.
        """
        request = make_asgi_request(headers=[(b"cookie", b"sid=abc; theme=dark")])
        self.assertIsInstance(request.cookies, Cookies)
        self.assertEqual(request.cookies.get("sid"), "abc")
        self.assertIs(request.cookies, request.cookies)

    def testStateIsAMutableNamespace(self) -> None:
        """
        Expose a mutable namespace shared by middleware and handlers.

        Validates the channel used to publish the session and the CSRF
        token without polluting the scope.
        """
        request = make_asgi_request()
        request.state.tenant = "acme"
        self.assertEqual(request.state.tenant, "acme")


class TestRequestClientInformation(TestCase):

    def testResolvesTheClientIpFromATuple(self) -> None:
        """
        Read the client address from an ASGI ``(host, port)`` pair.

        Validates the fallback used when no proxy middleware ran.
        """
        request = make_asgi_request()
        self.assertEqual(request.ip, "127.0.0.1")
        self.assertEqual(request.ip, "127.0.0.1")

    def testResolvesTheClientIpFromAPlainString(self) -> None:
        """
        Read the client address normalised by the proxy middleware.

        Validates the shape stored back into the scope by the adapter.
        """
        request = make_asgi_request(scope_overrides={"client": "10.0.0.7"})
        self.assertEqual(request.ip, "10.0.0.7")

    def testReportsAnUnknownClientAsNone(self) -> None:
        """
        Report a missing client address as ``None``.

        Validates that rate limiting can skip anonymous transports.
        """
        self.assertIsNone(make_asgi_request(remove=("client",)).ip)

    def testExposesTheClientPort(self) -> None:
        """
        Expose the client port published in the scope.

        Validates the accessor consumed by the request printer.
        """
        request = make_asgi_request(scope_overrides={"port": 51234})
        self.assertEqual(request.port, 51234)
        self.assertEqual(request.port, 51234)

    def testReportsAnUnknownPortAsNone(self) -> None:
        """
        Report a missing client port as ``None``.

        Validates the default for transports that do not publish it.
        """
        self.assertIsNone(make_asgi_request().port)

    def testForwardedDefaultsToAnEmptyMapping(self) -> None:
        """
        Report no forwarding metadata as an empty mapping.

        Validates that callers can index the result unconditionally.
        """
        self.assertEqual(make_asgi_request().forwarded, {})

    def testExposesForwardedMetadata(self) -> None:
        """
        Expose the forwarding metadata stored by the proxy middleware.

        Validates the accessor used to audit the original client.
        """
        request = make_asgi_request(
            scope_overrides={"forwarded": {"for": "10.0.0.7"}},
        )
        self.assertEqual(request.forwarded, {"for": "10.0.0.7"})
        self.assertEqual(request.forwarded, {"for": "10.0.0.7"})


class TestRequestIdentityHeaders(TestCase):

    def testExposesTheUserAgent(self) -> None:
        """
        Expose the user agent advertised by the client.

        Validates the accessor used for logging and analytics.
        """
        request = make_asgi_request(headers=[(b"user-agent", b"orionis/1.0")])
        self.assertEqual(request.userAgent, "orionis/1.0")

    def testReportsAMissingUserAgentAsNone(self) -> None:
        """
        Report a missing user agent as ``None``.

        Validates that header-less clients do not break logging.
        """
        self.assertIsNone(make_asgi_request().userAgent)

    def testExposesTheAuthorizationHeader(self) -> None:
        """
        Expose the raw authorization header.

        Validates the accessor used by custom authentication schemes.
        """
        request = make_asgi_request(headers=[(b"authorization", b"Basic abc")])
        self.assertEqual(request.authorization, "Basic abc")

    def testExtractsTheBearerToken(self) -> None:
        """
        Strip the scheme prefix from a bearer authorization header.

        Validates the accessor used by token guards.
        """
        request = make_asgi_request(headers=[(b"authorization", b"Bearer t0ken")])
        self.assertEqual(request.bearerToken, "t0ken")

    def testIgnoresANonBearerAuthorizationHeader(self) -> None:
        """
        Report ``None`` for a non-bearer authorization scheme.

        Validates that basic credentials are never mistaken for a token.
        """
        request = make_asgi_request(headers=[(b"authorization", b"Basic abc")])
        self.assertIsNone(request.bearerToken)

    def testReportsAMissingBearerTokenAsNone(self) -> None:
        """
        Report a missing authorization header as ``None``.

        Validates the guard protecting anonymous requests.
        """
        self.assertIsNone(make_asgi_request().bearerToken)

    def testExposesTheApiKeyHeader(self) -> None:
        """
        Expose the API key advertised by the client.

        Validates the accessor used by machine-to-machine guards.
        """
        request = make_asgi_request(headers=[(b"x-api-key", b"secret-key")])
        self.assertEqual(request.apiKey, "secret-key")

    def testExposesTheAcceptHeader(self) -> None:
        """
        Expose the raw accept header.

        Validates the value inspected during content negotiation.
        """
        request = make_asgi_request(headers=[(b"accept", b"text/html")])
        self.assertEqual(request.accept, "text/html")


class TestRequestContentNegotiation(TestCase):

    def testDetectsAJsonClient(self) -> None:
        """
        Detect a client that asked for JSON.

        Validates the branch that returns structured validation errors.
        """
        request = make_asgi_request(headers=[(b"accept", b"application/json")])
        self.assertTrue(request.wantsJson())

    def testDetectsAJsonSubtype(self) -> None:
        """
        Detect vendor media types ending in ``+json``.

        Validates support for JSON API style clients.
        """
        request = make_asgi_request(headers=[(b"accept", b"application/vnd.api+json")])
        self.assertTrue(request.wantsJson())

    def testDetectsAnHtmlClient(self) -> None:
        """
        Detect a browser asking for markup or anything at all.

        Validates the branch that renders the HTML error page.
        """
        self.assertTrue(
            make_asgi_request(headers=[(b"accept", b"text/html")]).wantsHtml(),
        )
        self.assertTrue(
            make_asgi_request(headers=[(b"accept", b"*/*")]).wantsHtml(),
        )

    def testDetectsAnXmlClient(self) -> None:
        """
        Detect a client asking for XML in either spelling.

        Validates the branch used by legacy integrations.
        """
        self.assertTrue(
            make_asgi_request(headers=[(b"accept", b"application/xml")]).wantsXml(),
        )
        self.assertTrue(
            make_asgi_request(headers=[(b"accept", b"text/xml")]).wantsXml(),
        )

    def testMatchesAnArbitraryMediaType(self) -> None:
        """
        Match any media type case-insensitively.

        Validates the general-purpose negotiation helper.
        """
        request = make_asgi_request(headers=[(b"accept", b"text/csv")])
        self.assertTrue(request.accepts("TEXT/CSV"))
        self.assertFalse(request.accepts("image/png"))

    def testTreatsAMissingAcceptHeaderAsNoPreference(self) -> None:
        """
        Report no preference when the accept header is absent.

        Validates the cached empty string used by the negotiation
        helpers.
        """
        request = make_asgi_request()
        self.assertFalse(request.wantsJson())
        self.assertFalse(request.wantsHtml())

    def testDetectsAnAjaxSubmission(self) -> None:
        """
        Detect a request issued by a JavaScript client.

        Validates the branch answering form posts with JSON.
        """
        request = make_asgi_request(
            headers=[(b"x-requested-with", b"XMLHttpRequest")],
        )
        self.assertTrue(request.isAjax())
        self.assertFalse(make_asgi_request().isAjax())


class TestRequestRouteParameters(TestCase):

    def testExposesEveryRouteParameter(self) -> None:
        """
        Expose the parameters extracted from the path.

        Validates the mapping forwarded to the handler by the container.
        """
        request = make_asgi_request(params={"id": 7})
        self.assertEqual(request.routeParams(), {"id": 7})

    def testReadsASingleRouteParameter(self) -> None:
        """
        Read one path parameter by name.

        Validates the accessor used inside middleware.
        """
        request = make_asgi_request(params={"id": 7})
        self.assertEqual(request.routeParam("id"), 7)

    def testReportsAnUnknownRouteParameterAsNone(self) -> None:
        """
        Report an unknown parameter name as ``None``.

        Validates that optional segments do not raise.
        """
        self.assertIsNone(make_asgi_request().routeParam("missing"))


class TestRequestCsrfToken(TestCase):

    def testReportsNoTokenBeforeTheMiddlewareRuns(self) -> None:
        """
        Report ``None`` when the CSRF middleware has not run.

        Validates that API routes can read the accessor safely.
        """
        request = make_asgi_request()
        self.assertIsNone(request.csrfToken())
        self.assertIsNone(request.csrf_token)

    def testExposesTheTokenPublishedByTheMiddleware(self) -> None:
        """
        Expose the token published on the request state.

        Validates both the method and the template-friendly property.
        """
        request = make_asgi_request()
        request.state.csrf_token = _CSRF_VALUE
        self.assertEqual(request.csrfToken(), _CSRF_VALUE)
        self.assertEqual(request.csrf_token, _CSRF_VALUE)


class TestRequestBodyReading(TestCase):

    async def testStreamsTheBodyInChunks(self) -> None:
        """
        Yield the body as it arrives from the transport.

        Validates the generator consumed by streaming handlers.
        """
        request = make_asgi_request(body=b"payload")
        self.assertEqual([chunk async for chunk in request.stream()], [b"payload"])

    async def testBufferTheBodyOnce(self) -> None:
        """
        Buffer the body and reuse it on later reads.

        Validates that a handler can read the payload twice.
        """
        request = make_asgi_request(body=b"payload")
        self.assertEqual(await request.body(), b"payload")
        self.assertEqual(await request.body(), b"payload")

    async def testExposesTheRawBody(self) -> None:
        """
        Expose the buffered body through the raw accessor.

        Validates the alias used by signature verification middleware.
        """
        request = make_asgi_request(body=b"payload")
        self.assertEqual(await request.raw(), b"payload")

    async def testDecodesTheBodyAsText(self) -> None:
        """
        Decode the body as UTF-8 text.

        Validates the accessor used by webhook handlers.
        """
        request = make_asgi_request(body="ñandú".encode())
        self.assertEqual(await request.text(), "ñandú")


class TestRequestJsonParsing(TestCase):

    async def testParsesAJsonBody(self) -> None:
        """
        Decode a JSON body and cache the decoded value.

        Validates the accessor used by API controllers.
        """
        request = make_asgi_request(
            body=b'{"a":1}',
            headers=[(b"content-type", b"application/json")],
        )
        self.assertEqual(await request.json(), {"a": 1})
        self.assertEqual(await request.json(), {"a": 1})

    async def testAcceptsAJsonSubtype(self) -> None:
        """
        Decode bodies advertised with a ``+json`` media type.

        Validates support for vendor-specific JSON payloads.
        """
        request = make_asgi_request(
            body=b'{"a":1}',
            headers=[(b"content-type", b"application/vnd.api+json")],
        )
        self.assertEqual(await request.json(), {"a": 1})

    async def testCachesAJsonNullLiteral(self) -> None:
        """
        Cache a decoded ``null`` literal instead of re-reading the body.

        Validates the sentinel that distinguishes ``null`` from
        "not parsed yet".
        """
        request = make_asgi_request(
            body=b"null",
            headers=[(b"content-type", b"application/json")],
        )
        self.assertIsNone(await request.json())
        self.assertIsNone(await request.json())

    async def testRejectsANonJsonContentType(self) -> None:
        """
        Reject a body whose media type is not JSON.

        Validates the guard protecting handlers from silent mis-parsing.
        """
        request = make_asgi_request(
            body=b'{"a":1}',
            headers=[(b"content-type", b"text/plain")],
        )
        with self.assertRaises(UnsupportedMediaTypeException):
            await request.json()

    async def testRejectsAnEmptyJsonBody(self) -> None:
        """
        Reject an empty JSON body.

        Validates the diagnostic returned for a missing payload.
        """
        request = make_asgi_request(
            headers=[(b"content-type", b"application/json")],
        )
        with self.assertRaises(ValueError):
            await request.json()

    async def testRejectsAMalformedJsonBody(self) -> None:
        """
        Reject a body that is not valid JSON.

        Validates that decoding errors are reported as value errors.
        """
        request = make_asgi_request(
            body=b"{not json}",
            headers=[(b"content-type", b"application/json")],
        )
        with self.assertRaises(ValueError):
            await request.json()


class TestRequestOtherParsers(TestCase):

    async def testParsesAnXmlBody(self) -> None:
        """
        Parse an XML body into an element tree.

        Validates the hardened parser used by legacy integrations.
        """
        request = make_asgi_request(body=b"<root><a>1</a></root>")
        element = await request.xml()
        self.assertEqual(element.tag, "root")

    async def testRejectsMalformedXml(self) -> None:
        """
        Reject an XML body that cannot be parsed.

        Validates that malformed payloads surface as parse errors.
        """
        request = make_asgi_request(body=b"<root>")
        with self.assertRaises(ParseError):
            await request.xml()

    async def testDecodesAMessagePackBody(self) -> None:
        """
        Decode a MessagePack body.

        Validates the binary payload format used by internal services.
        """
        request = make_asgi_request(body=msgpack.encode({"a": 1}))
        self.assertEqual(await request.msgpack(), {"a": 1})

    async def testParsesAUrlEncodedBody(self) -> None:
        """
        Parse a URL-encoded body and cache the parsed fields.

        Validates the accessor used by classic form posts.
        """
        request = make_asgi_request(
            body=b"a=1&b=2",
            headers=[(b"content-type", b"application/x-www-form-urlencoded")],
        )
        self.assertEqual(await request.formUrlEncoded(), {"a": "1", "b": "2"})
        self.assertEqual(await request.formUrlEncoded(), {"a": "1", "b": "2"})

    async def testRejectsANonUrlEncodedContentType(self) -> None:
        """
        Reject a body whose media type is not URL-encoded.

        Validates the guard protecting form handlers.
        """
        request = make_asgi_request(
            body=b"a=1",
            headers=[(b"content-type", b"text/plain")],
        )
        with self.assertRaises(UnsupportedMediaTypeException):
            await request.formUrlEncoded()


class TestRequestMultipartParsing(TestCase):

    def _makeMultipartRequest(self, fields: list[tuple[str, str]]) -> Request:
        """
        Build a request carrying a multipart payload.

        Parameters
        ----------
        fields : list[tuple[str, str]]
            Ordered field name and value pairs.

        Returns
        -------
        Request
            Request advertising ``multipart/form-data``.
        """
        return make_asgi_request(
            body=make_multipart_body(fields),
            headers=[(
                b"content-type",
                f'multipart/form-data; boundary="{_BOUNDARY}"'.encode(),
            )],
        )

    async def testParsesMultipartFields(self) -> None:
        """
        Parse multipart fields and cache the resulting form.

        Validates the streaming parser used by file uploads.
        """
        request = self._makeMultipartRequest([("a", "1")])
        form = await request.form()
        self.assertIsInstance(form, FormData)
        self.assertEqual(form.get("a"), "1")
        self.assertIs(await request.form(), form)

    async def testRejectsANonMultipartContentType(self) -> None:
        """
        Reject a body whose media type is not multipart.

        Validates the guard protecting the streaming parser.
        """
        request = make_asgi_request(
            headers=[(b"content-type", b"application/json")],
        )
        with self.assertRaises(UnsupportedMediaTypeException):
            await request.form()

    async def testRejectsAMissingBoundary(self) -> None:
        """
        Reject a multipart body without a boundary parameter.

        Validates the diagnostic returned for a malformed header.
        """
        request = make_asgi_request(
            headers=[(b"content-type", b"multipart/form-data")],
        )
        with self.assertRaises(ValueError):
            await request.form()


class TestRequestPayloadDispatch(TestCase):

    async def testFallsBackToRawBytesWithoutAContentType(self) -> None:
        """
        Return the raw body when no media type is advertised.

        Validates the default for opaque payloads.
        """
        request = make_asgi_request(body=b"opaque")
        self.assertEqual(await request.payload(), b"opaque")

    async def testDispatchesToTheRegisteredParser(self) -> None:
        """
        Parse the body with the parser registered for its media type.

        Validates the registry lookup performed on every request.
        """
        request = make_asgi_request(
            body=b'{"a":1}',
            headers=[(b"content-type", b"application/json")],
        )
        self.assertEqual(await request.payload(), {"a": 1})

    async def testFallsBackToRawBytesForAnUnknownMediaType(self) -> None:
        """
        Return the raw body when no parser matches the media type.

        Validates that unknown formats reach the handler untouched.
        """
        request = make_asgi_request(
            body=b"raw",
            headers=[(b"content-type", b"application/vnd.unknown")],
        )
        self.assertEqual(await request.payload(), b"raw")

    async def testDelegatesMultipartToTheStreamingParser(self) -> None:
        """
        Route multipart payloads to the streaming parser.

        Validates that the registry never receives a pre-buffered
        multipart body.
        """
        request = make_asgi_request(
            body=make_multipart_body([("a", "1")]),
            headers=[(
                b"content-type",
                f"multipart/form-data; boundary={_BOUNDARY}".encode(),
            )],
        )
        self.assertIsInstance(await request.payload(), FormData)

    async def testUsesTheInjectedRegistry(self) -> None:
        """
        Honour a media-type registry supplied by the caller.

        Validates the extension point used to add custom formats.
        """
        registry = MediaTypeRegistry(
            {"application/vnd.custom": lambda raw: {"decoded": raw.decode()}},
        )
        request = make_asgi_request(
            body=b"value",
            headers=[(b"content-type", b"application/vnd.custom")],
            registry=registry,
        )
        self.assertEqual(await request.payload(), {"decoded": "value"})

    def testDefaultsToTheSharedRegistry(self) -> None:
        """
        Fall back to the framework registry when none is injected.

        Validates the default wiring performed by the kernel.
        """
        request = make_asgi_request()
        self.assertIs(request._Request__registry, DEFAULT_MEDIA_TYPES)


class TestRequestDataDictionary(TestCase):

    async def testParsesAJsonObject(self) -> None:
        """
        Return a JSON object as a flat dictionary and cache it.

        Validates the payload handed to schema validation.
        """
        request = make_asgi_request(
            body=b'{"a":1}',
            headers=[(b"content-type", b"application/json")],
        )
        self.assertEqual(await request.data(), {"a": 1})
        self.assertEqual(await request.data(), {"a": 1})

    async def testReusesAnAlreadyDecodedJsonBody(self) -> None:
        """
        Reuse the JSON value decoded by a previous call.

        Validates that the body is never read twice from the transport.
        """
        request = make_asgi_request(
            body=b'{"a":1}',
            headers=[(b"content-type", b"application/json")],
        )
        await request.json()
        self.assertEqual(await request.data(), {"a": 1})

    async def testRejectsAnEmptyJsonBody(self) -> None:
        """
        Reject an empty JSON body when building the dictionary.

        Validates the diagnostic returned for a missing payload.
        """
        request = make_asgi_request(
            headers=[(b"content-type", b"application/json")],
        )
        with self.assertRaises(ValueError):
            await request.data()

    async def testRejectsAMalformedJsonBody(self) -> None:
        """
        Reject a malformed JSON body when building the dictionary.

        Validates that decoding failures surface as value errors.
        """
        request = make_asgi_request(
            body=b"{oops}",
            headers=[(b"content-type", b"application/json")],
        )
        with self.assertRaises(ValueError):
            await request.data()

    async def testRejectsAJsonArray(self) -> None:
        """
        Reject a JSON payload that is not an object.

        Validates that schema validation always receives a mapping.
        """
        request = make_asgi_request(
            body=b"[1,2]",
            headers=[(b"content-type", b"application/json")],
        )
        with self.assertRaises(TypeError):
            await request.data()

    async def testCollapsesRepeatedUrlEncodedFields(self) -> None:
        """
        Collapse repeated URL-encoded keys into a list.

        Validates the multi-value semantics of HTML checkboxes.
        """
        request = make_asgi_request(
            body=b"tag=a&tag=b&name=x",
            headers=[(b"content-type", b"application/x-www-form-urlencoded")],
        )
        self.assertEqual(
            await request.data(),
            {"tag": ["a", "b"], "name": "x"},
        )

    async def testCollapsesRepeatedMultipartFields(self) -> None:
        """
        Collapse repeated multipart keys into a list.

        Validates that a third occurrence is appended to the existing
        list instead of replacing it.
        """
        request = make_asgi_request(
            body=make_multipart_body(
                [("tag", "a"), ("tag", "b"), ("tag", "c"), ("name", "x")],
            ),
            headers=[(
                b"content-type",
                f"multipart/form-data; boundary={_BOUNDARY}".encode(),
            )],
        )
        self.assertEqual(
            await request.data(),
            {"tag": ["a", "b", "c"], "name": "x"},
        )

    async def testDecodesAMessagePackObject(self) -> None:
        """
        Return a MessagePack map as a flat dictionary.

        Validates the binary counterpart of the JSON path.
        """
        request = make_asgi_request(
            body=msgpack.encode({"a": 1}),
            headers=[(b"content-type", b"application/msgpack")],
        )
        self.assertEqual(await request.data(), {"a": 1})

    async def testRejectsAMalformedMessagePackBody(self) -> None:
        """
        Reject a MessagePack body that cannot be decoded.

        Validates that decoding failures surface as value errors.
        """
        request = make_asgi_request(
            body=b"\xc1",
            headers=[(b"content-type", b"application/msgpack")],
        )
        with self.assertRaises(ValueError):
            await request.data()

    async def testRejectsAMessagePackArray(self) -> None:
        """
        Reject a MessagePack payload that is not a map.

        Validates that schema validation always receives a mapping.
        """
        request = make_asgi_request(
            body=msgpack.encode([1, 2]),
            headers=[(b"content-type", b"application/msgpack")],
        )
        with self.assertRaises(TypeError):
            await request.data()

    async def testRejectsAnUnsupportedContentType(self) -> None:
        """
        Reject a media type that cannot become a dictionary.

        Validates the diagnostic naming the offending content type.
        """
        request = make_asgi_request(
            body=b"<xml/>",
            headers=[(b"content-type", b"application/xml")],
        )
        with self.assertRaises(UnsupportedMediaTypeException) as captured:
            await request.data()
        self.assertIn("application/xml", str(captured.exception))

    async def testNamesAMissingContentTypeAsUnknown(self) -> None:
        """
        Report a missing content type as ``unknown``.

        Validates the fallback used in the error message.
        """
        request = make_asgi_request(body=b"raw")
        with self.assertRaises(UnsupportedMediaTypeException) as captured:
            await request.data()
        self.assertIn("unknown", str(captured.exception))

    async def testStripsCredentialFieldsOnlyWhenFlashed(self) -> None:
        """
        Return the submitted payload verbatim, credentials included.

        Validates that stripping happens when flashing, not when parsing,
        so authentication handlers still receive the password.
        """
        request = make_asgi_request(
            body=b"email=a%40b.test&password=hunter2",
            headers=[(b"content-type", b"application/x-www-form-urlencoded")],
        )
        self.assertEqual(
            await request.data(),
            {"email": "a@b.test", _CREDENTIAL_FIELD: "hunter2"},
        )
