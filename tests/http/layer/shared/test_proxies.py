from __future__ import annotations
from ipaddress import ip_address
from typing import TYPE_CHECKING
from orionis.http.layer.shared import proxies as proxies_module
from orionis.http.layer.shared.proxies import ProxiesMiddleware
from orionis.test import TestCase
from tests.http.test_support import make_adapter, replace_attribute

if TYPE_CHECKING:
    from ipaddress import IPv4Address, IPv6Address

class TestProxyAddressResolution(TestCase):
    """Preserve proxy trust while avoiding redundant peer address parsing."""

    def testExactProxyPeersDoNotRequireAddressParsing(self) -> None:
        """Match configured single-host peers without parsing each request.

        Returns
        -------
        None
            Repeated IPv4 and IPv6 peers retain forwarding metadata.
        """
        cases = (
            ("127.0.0.1", "127.0.0.1"),
            ("192.0.2.7", "192.0.2.7/32"),
            ("2001:db8::7", "2001:db8::7/128"),
        )
        parsed: list[str] = []

        def record_parse(value: str) -> IPv4Address | IPv6Address:
            """Record each address passed to the standard parser.

            Parameters
            ----------
            value : str
                Address supplied by the proxy middleware.

            Returns
            -------
            IPv4Address | IPv6Address
                Parsed address returned without changing validation.
            """
            parsed.append(value)
            return ip_address(value)

        for peer, trusted in cases:
            with self.subTest(peer=peer):
                parsed.clear()
                middleware = ProxiesMiddleware({"trusted_proxies": [trusted]})
                with replace_attribute(proxies_module, "ip_address", record_parse):
                    for _ in range(3):
                        adapter = make_adapter([])
                        adapter.setClient(peer)
                        self.assertIs(middleware.handle(adapter), adapter)
                        self.assertEqual(adapter["forwarded"], {
                            "client": peer, "proxies": [], "chain": [peer],
                        })
                self.assertEqual(parsed, [])

    def testExactProxyStillValidatesTheForwardedChain(self) -> None:
        """Parse forwarded hops and stop at the first untrusted address.

        Returns
        -------
        None
            An untrusted hop prevents trusting addresses farther to its left.
        """
        middleware = ProxiesMiddleware({"trusted_proxies": ["127.0.0.1"]})
        adapter = make_adapter([
            (b"x-forwarded-for", b"203.0.113.8, invalid, 198.51.100.9, 127.0.0.1"),
            (b"x-forwarded-proto", b"https"),
        ])
        adapter.setClient("127.0.0.1")

        middleware.handle(adapter)

        self.assertEqual(adapter.client(), "198.51.100.9")
        self.assertEqual(adapter.scheme(), "https")
        self.assertEqual(adapter["forwarded"], {
            "client": "198.51.100.9",
            "proxies": ["203.0.113.8", "127.0.0.1"],
            "chain": ["203.0.113.8", "198.51.100.9", "127.0.0.1"],
        })

    def testCidrAndEquivalentIpv6PeersRetainNetworkValidation(self) -> None:
        """Resolve networks and noncanonical peer spellings through IP parsing.

        Returns
        -------
        None
            CIDR ranges, private shorthand, and equivalent IPv6 forms are trusted.
        """
        cases = (
            ("192.0.2.7", "192.0.2.0/24"),
            ("2001:db8:1::7", "2001:db8:1::/48"),
            ("10.1.2.3", "private"),
            ("2001:0DB8:0000:0000:0000:0000:0000:0007", "2001:db8::7/128"),
        )
        for peer, trusted in cases:
            with self.subTest(peer=peer):
                middleware = ProxiesMiddleware({"trusted_proxies": [trusted]})
                adapter = make_adapter([
                    (b"x-forwarded-for", b"198.51.100.9"),
                    (b"x-forwarded-proto", b"https"),
                ])
                adapter.setClient(peer)

                middleware.handle(adapter)

                self.assertEqual(adapter.client(), "198.51.100.9")
                self.assertEqual(adapter.scheme(), "https")
                self.assertEqual(adapter["forwarded"], {
                    "client": "198.51.100.9",
                    "proxies": [],
                    "chain": ["198.51.100.9"],
                })

    def testTrustIsLocalToEachMiddlewareConfiguration(self) -> None:
        """Keep exact peer trust independent across middleware instances.

        Returns
        -------
        None
            Untrusted, malformed, and disabled peers cannot apply forwarding.
        """
        cases = (
            ("127.0.0.1", ["127.0.0.1"], True),
            ("127.0.0.1", ["192.0.2.7"], False),
            ("invalid", ["127.0.0.1"], False),
            ("127.0.0.1", [], False),
        )
        for peer, trusted, accepted in cases:
            with self.subTest(peer=peer, trusted=trusted):
                middleware = ProxiesMiddleware({"trusted_proxies": trusted})
                adapter = make_adapter([
                    (b"x-forwarded-for", b"198.51.100.9"),
                    (b"x-forwarded-proto", b"https"),
                ])
                adapter.setClient(peer)

                middleware.handle(adapter)

                if accepted:
                    self.assertEqual(adapter.client(), "198.51.100.9")
                    self.assertEqual(adapter.scheme(), "https")
                    self.assertIn("forwarded", adapter)
                else:
                    self.assertEqual(adapter.client(), peer)
                    self.assertEqual(adapter.scheme(), "http")
                    self.assertNotIn("forwarded", adapter)
