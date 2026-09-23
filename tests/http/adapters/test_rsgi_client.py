from orionis.http.adapters.request.rsgi import RSGITransportAdapter
from orionis.http.layer.shared.proxies import ProxiesMiddleware
from orionis.test import TestCase
from tests.http.test_kernel import _StubRsgiHeaders, _StubRsgiScope


def _make_scope(
    client: str | None,
    headers: dict[str, list[str]] | None = None,
) -> _StubRsgiScope:
    """Build an RSGI scope with a selected peer and forwarding headers.

    Parameters
    ----------
    client : str | None
        Socket address supplied by the server.
    headers : dict[str, list[str]] | None
        Additional request headers mapped to all their values.

    Returns
    -------
    _StubRsgiScope
        Scope exposing the complete adapter interface.
    """
    scope = _StubRsgiScope("/")
    scope.client = client
    if headers is not None:
        scope.headers = _StubRsgiHeaders(headers)
    return scope


class TestRsgiClient(TestCase):

    def testClientNormalizesIpv6AndPreservesCacheAndOverrides(self) -> None:
        """Normalize socket hosts while retaining port and cached overrides."""
        cases = (
            ("[::1]:1234", "::1"),
            ("[2001:db8::7]:1234", "2001:db8::7"),
            ("[::ffff:192.0.2.7]:1234", "::ffff:192.0.2.7"),
            ("[fe80::1%3]:1234", "fe80::1%3"),
            ("::1:1234", "::1"),
            ("127.0.0.1:1234", "127.0.0.1"),
        )
        for raw, expected in cases:
            scope = _make_scope(raw)
            adapter = RSGITransportAdapter(scope)
            self.assertEqual(adapter.getScope()["client"], raw)
            self.assertEqual(adapter.client(), expected)
            self.assertEqual(adapter["client"], expected)
            self.assertEqual(adapter["port"], 1234)
            self.assertEqual(scope.client, raw)

            scope.client = "192.0.2.1:9876"
            self.assertEqual(adapter.client(), expected)
            adapter.setClient("2001:db8::99")
            self.assertEqual(adapter.client(), "2001:db8::99")
            self.assertEqual(adapter.getScope()["client"], "2001:db8::99")
            self.assertEqual(adapter.getScope()["port"], 1234)

    def testUnavailableClientAndEarlyOverrideRemainLazy(self) -> None:
        """Cache absent peers and honor an override before parsing the scope."""
        for raw in (None, ""):
            scope = _make_scope(raw)
            adapter = RSGITransportAdapter(scope)
            self.assertIsNone(adapter.client())
            self.assertNotIn("port", adapter)
            scope.client = "[::1]:1234"
            self.assertIsNone(adapter.client())
            adapter.setClient("::2")
            self.assertEqual(adapter.client(), "::2")
            self.assertNotIn("port", adapter)

        adapter = RSGITransportAdapter(_make_scope("[::1]:1234"))
        adapter.setClient("192.0.2.10")
        self.assertEqual(adapter.client(), "192.0.2.10")
        self.assertNotIn("port", adapter)

    def testTrustedIpv6AndIpv4PeersApplyForwarding(self) -> None:
        """Trust normalized peers and apply the validated forwarding chain."""
        cases = (
            ("[::1]:1234", "::1/128", "::1"),
            ("[2001:db8:123::7]:1234", "2001:db8:123::/48", "2001:db8:123::7"),
            ("127.0.0.1:1234", "127.0.0.1/32", "127.0.0.1"),
        )
        real_ip = "2001:db8:ffff::123"
        for raw, trusted, proxy in cases:
            adapter = RSGITransportAdapter(_make_scope(raw, {
                "x-forwarded-for": [f"{real_ip}, {proxy}"],
                "x-forwarded-proto": ["https"],
            }))
            middleware = ProxiesMiddleware({"trusted_proxies": [trusted]})

            self.assertIs(middleware.handle(adapter), adapter)
            self.assertEqual(adapter.client(), real_ip)
            self.assertEqual(adapter.scheme(), "https")
            self.assertEqual(adapter["port"], 1234)
            self.assertEqual(adapter["forwarded"], {
                "client": real_ip,
                "proxies": [proxy],
                "chain": [real_ip, proxy],
            })

    def testUntrustedIpv6AndIpv4PeersIgnoreForwarding(self) -> None:
        """Preserve the direct peer and scheme when proxy trust does not match."""
        cases = (
            ("[::1]:1234", "2001:db8:123::/48", "::1"),
            ("[2001:db8:456::7]:1234", "2001:db8:123::/48", "2001:db8:456::7"),
            ("192.0.2.10:1234", "127.0.0.1/32", "192.0.2.10"),
        )
        for raw, trusted, expected in cases:
            adapter = RSGITransportAdapter(_make_scope(raw, {
                "x-forwarded-for": ["198.51.100.9"],
                "x-forwarded-proto": ["https"],
            }))
            middleware = ProxiesMiddleware({"trusted_proxies": [trusted]})

            self.assertIs(middleware.handle(adapter), adapter)
            self.assertEqual(adapter.client(), expected)
            self.assertEqual(adapter.scheme(), "http")
            self.assertEqual(adapter["port"], 1234)
            self.assertNotIn("forwarded", adapter)
