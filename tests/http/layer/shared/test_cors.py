from orionis.environment import Env
from orionis.http.layer.shared.cors import CORSException, CORSMiddleware
from orionis.http.responses import Response
from orionis.test import TestCase
from tests.http.test_support import make_adapter, replace_attribute

class TestCORSLifecycle(TestCase):
    """Exercise preflight and ordinary cross-origin response behavior."""

    def testDefaultOriginsAllowAnyOriginForRequestsAndPreflights(self) -> None:
        """Publish wildcard origins when no origin policy was configured.

        Returns
        -------
        None
            Ordinary and preflight responses allow arbitrary request origins.
        """
        with replace_attribute(
            Env, "get", lambda _key, default=None: default,
        ):
            middleware = CORSMiddleware({})

        for origin in (b"https://example.com", b"https://other.example"):
            with self.subTest(origin=origin):
                adapter = make_adapter([(b"origin", origin)])
                self.assertIsNone(middleware.before(adapter))
                response = middleware.after(adapter, Response())
                self.assertEqual(
                    response.getHeader("access-control-allow-origin"), ["*"],
                )
                self.assertIsNone(
                    response.getHeader("access-control-allow-credentials"),
                )

                preflight = make_adapter([
                    (b"origin", origin),
                    (b"access-control-request-method", b"GET"),
                ], method="OPTIONS")
                preflight_response = middleware.before(preflight)
                if preflight_response is None:
                    self.fail("Expected a CORS preflight response.")
                self.assertEqual(preflight_response.getStatusCode(), 204)
                self.assertEqual(
                    preflight_response.getHeader("access-control-allow-origin"),
                    ["*"],
                )

    def testDefaultWildcardOriginsStillRejectCredentials(self) -> None:
        """Reject credentialed requests without an explicit origin allowlist.

        Returns
        -------
        None
            Default and normalized wildcard origins retain credential validation.
        """
        with replace_attribute(
            Env, "get", lambda _key, default=None: default,
        ):
            for config in ({}, {"allow_origins": []}, {"allow_origins": None}):
                with (
                    self.subTest(config=config),
                    self.assertRaisesRegex(CORSException, "wildcard origins"),
                ):
                    CORSMiddleware({**config, "allow_credentials": True})

    def testExplicitOriginsStillRejectOtherOrigins(self) -> None:
        """Keep configured origin restrictions despite the wildcard default.

        Returns
        -------
        None
            Unlisted origins receive no cross-origin permission headers.
        """
        middleware = CORSMiddleware({
            "allow_origins": ["https://example.com"],
            "allow_origin_regex": None,
        })
        adapter = make_adapter([(b"origin", b"https://other.example")])
        response = middleware.after(adapter, Response())
        self.assertIsNone(response.getHeader("access-control-allow-origin"))
        preflight = make_adapter([
            (b"origin", b"https://other.example"),
            (b"access-control-request-method", b"GET"),
        ], method="OPTIONS")
        self.assertIsNone(middleware.before(preflight))

    def testChecksOrdinaryRequestOriginOnlyWhenWritingHeaders(self) -> None:
        """Defer ordinary request origin validation until a response exists.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        middleware = CORSMiddleware({"allow_origins": ["https://example.com"]})
        adapter = make_adapter([(b"origin", b"https://example.com")])
        origins: list[str] = []

        def allowed_origin(_middleware: CORSMiddleware, origin: str) -> bool:
            """Record the checked origin and accept it for this request.

            Parameters
            ----------
            _middleware : CORSMiddleware
                Value supplied for ``_middleware``.
            origin : str
                Value supplied for ``origin``.

            Returns
            -------
            bool
                Value produced by the helper.
            """
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
        """Publish the configured origin, credentials, methods, and header policy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
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
