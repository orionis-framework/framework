from orionis.http.layer.shared.security import SecurityMiddleware
from orionis.http.responses import Response
from orionis.test import TestCase
from tests.http.layer.shared._support import make_adapter

class _DefaultResponses:
    """Produce plain error responses for middleware assertions."""

    @staticmethod
    async def error(*, status_code: int, content: str, **_kwargs: object) -> Response:
        """Return the requested error status and body."""
        return Response(status_code=status_code, content=content)

class TestSecurityHeaderChecks(TestCase):
    """Preserve host and header policies across middleware changes."""

    async def testRejectsDuplicateHostHeadersRegardlessOfCase(self) -> None:
        """Reject two Host fields even when their casing differs."""
        middleware = SecurityMiddleware({}, _DefaultResponses())
        response = await middleware.handle(make_adapter([
            (b"Host", b"example.com"), (b"host", b"other.example.com"),
        ]))
        self.assertEqual(response.getStatusCode(), 400)

    async def testMatchesExactAndWildcardHosts(self) -> None:
        """Match wildcard suffixes at a domain boundary and retain exact hosts."""
        middleware = SecurityMiddleware(
            {"allowed_hosts": ["*.example.com", "internal.local"]},
            _DefaultResponses(),
        )
        for hostname in (
            b"example.com", b"api.example.com", b"API.EXAMPLE.COM:443",
            b"internal.local",
        ):
            with self.subTest(hostname=hostname):
                self.assertIsNone(await middleware.handle(make_adapter([
                    (b"host", hostname),
                ])))
        for hostname in (b"evil-example.com", b"example.com.evil", b"unknown"):
            with self.subTest(hostname=hostname):
                response = await middleware.handle(make_adapter([(b"host", hostname)]))
                self.assertEqual(response.getStatusCode(), 400)

    async def testRetainsHeaderInjectionValidation(self) -> None:
        """Reject carriage returns and line feeds before accepting the request."""
        middleware = SecurityMiddleware({}, _DefaultResponses())
        for headers in (
            [(b"x-value", b"text\r\ninvalid")], [(b"x-invalid\n", b"text")],
        ):
            response = await middleware.handle(make_adapter(headers))
            self.assertEqual(response.getStatusCode(), 400)
