from orionis.http.layer.shared.cors import CORSMiddleware
from orionis.http.responses import Response
from orionis.test import TestCase
from tests.http._support import replace_attribute
from tests.http.layer.shared._support import make_adapter

class TestCORSLifecycle(TestCase):
    """Exercise preflight and ordinary cross-origin response behavior."""

    def testChecksOrdinaryRequestOriginOnlyWhenWritingHeaders(self) -> None:
        """Defer ordinary request origin validation until a response exists."""
        middleware = CORSMiddleware({"allow_origins": ["https://example.com"]})
        adapter = make_adapter([(b"origin", b"https://example.com")])
        origins: list[str] = []

        def allowed_origin(_middleware: CORSMiddleware, origin: str) -> bool:
            """Record the checked origin and accept it for this request."""
            origins.append(origin)
            return True

        with replace_attribute(
            CORSMiddleware, "_CORSMiddleware__isAllowedOrigin", allowed_origin,
        ):
            self.assertIsNone(middleware.before(adapter))
            self.assertEqual(origins, [])
            response = middleware.after(adapter, Response())
            self.assertEqual(origins, ["https://example.com"])
        self.assertEqual(
            response.getHeader("access-control-allow-origin"),
            ["https://example.com"],
        )

    def testPreflightRetainsCredentialsRequestedHeadersAndVary(self) -> None:
        """Publish the configured origin, credentials, methods, and header policy."""
        middleware = CORSMiddleware({
            "allow_origins": ["https://example.com"],
            "allow_credentials": True, "allow_methods": ["GET", "POST"],
            "allow_headers": ["*"],
        })
        adapter = make_adapter([
            (b"origin", b"https://example.com"),
            (b"access-control-request-method", b"POST"),
            (b"access-control-request-headers", b"x-token"),
        ], method="OPTIONS")
        response = middleware.before(adapter)
        self.assertEqual(response.getStatusCode(), 204)
        self.assertEqual(
            response.getHeader("access-control-allow-credentials"), ["true"],
        )
        self.assertEqual(
            response.getHeader("access-control-allow-headers"), ["x-token"],
        )
        self.assertEqual(
            response.getHeader("access-control-allow-methods"), ["GET, POST"],
        )
        self.assertIn("origin", response.getHeader("vary")[0])
