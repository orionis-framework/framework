import math
from dataclasses import FrozenInstanceError, fields
from orionis.foundation.config.mcp.entities.mcp import McpConfig
from orionis.mcp.config import McpConfig as PublicMcpConfig
from orionis.test import TestCase

class TestMcpConfig(TestCase):
    """Verify finite budgets and an explicit browser-origin trust boundary."""

    def testDefaultsExportOneConfigTypeWithFrozenFields(self):
        """Keep shared configuration fields frozen and origin lists independent.

        Returns
        -------
        None
            Verify the exported type, independent defaults, and frozen fields.
        """
        self.assertIs(PublicMcpConfig, McpConfig)
        configured = McpConfig()
        self.assertEqual(configured.allowed_origins, [])
        self.assertIsInstance(configured.allowed_origins, list)
        self.assertIsNot(configured.allowed_origins, McpConfig().allowed_origins)
        self.assertLessEqual(configured.default_page_size, configured.max_page_size)
        with self.assertRaises(FrozenInstanceError):
            configured.max_request_size = 0

    def testEveryIntegerBudgetRejectsBoolNonIntegerAndZero(self):
        """Reject values that disable or silently coerce security limits.

        Returns
        -------
        None
            Confirm every integer budget rejects invalid values.
        """
        for field in fields(McpConfig):
            if field.name in {"allowed_origins", "subscription_keepalive"}:
                continue
            for value in (True, "32", 1.5, 0, -1):
                with (
                    self.subTest(field=field.name, value=value),
                    self.assertRaises(
                        (TypeError, ValueError),
                    ),
                ):
                    McpConfig(**{field.name: value})

    def testKeepaliveAndPageSizeLimits(self):
        """Prevent busy-loop keepalives and impossible default pagination.

        Returns
        -------
        None
            Check keepalive bounds and the relationship between page sizes.
        """
        for value in (True, 0, -1, math.inf, -math.inf, math.nan, "15"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                McpConfig(subscription_keepalive=value)
        with self.assertRaises(ValueError):
            McpConfig(default_page_size=101, max_page_size=100)

    def testOriginsRequireExplicitHttpAuthorities(self):
        """Reject wildcard, credentialed, malformed, and path-bearing origins.

        Returns
        -------
        None
            Verify malformed or non-HTTP origins fail configuration validation.
        """
        for origin in (
            "*",
            "null",
            "",
            "https://*.example.com",
            "https://example.com/",
            "https://user:pass@example.com",
            "https://example.com?",
            "https://example.com#",
            "https://example.com\\@evil.test",
            "https://example.com\n",
            "file:///tmp",
            "http://localhost:0",
            "http://localhost:65536",
            "http://localhost:",
            "http://[::1",
        ):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                McpConfig(allowed_origins=(origin,))
        for origins in ("https://example.com", (None,), {"https://example.com"}):
            with self.subTest(origins=origins), self.assertRaises(TypeError):
                McpConfig(allowed_origins=origins)

    def testValidOriginCollectionIsCopiedToAList(self):
        """Keep configured origin lists independent from the caller's list.

        Returns
        -------
        None
            Confirm later caller mutations do not change allowed origins.
        """
        origins = ["https://example.com", "http://127.0.0.1:8000", "http://[::1]:8000"]
        configured = McpConfig(allowed_origins=origins)
        origins.append("https://evil.test")
        self.assertEqual(configured.allowed_origins, origins[:-1])
        self.assertIsNot(configured.allowed_origins, origins)

    def testTupleOriginsRemainAcceptedAsLists(self):
        """Preserve existing tuple inputs while exposing origin lists.

        Returns
        -------
        None
            Confirm tuple inputs are copied to the public list representation.
        """
        origins = ("https://example.com",)
        configured = McpConfig(allowed_origins=origins)
        self.assertEqual(configured.allowed_origins, list(origins))
