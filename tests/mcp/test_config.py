import math
from dataclasses import FrozenInstanceError, fields
from orionis.foundation.config.mcp.entities.mcp import McpConfig
from orionis.mcp.config import McpConfig as PublicMcpConfig
from orionis.test import TestCase

class TestMcpConfig(TestCase):
    """Verify finite budgets and an explicit browser-origin trust boundary."""

    def test_defaults_are_immutable_and_export_one_config_type(self):
        """Keep shared framework and MCP configuration identical and frozen.

        Returns
        -------
        None
            Verify the exported type, immutable defaults, and frozen fields.
        """
        self.assertIs(PublicMcpConfig, McpConfig)
        configured = McpConfig()
        self.assertEqual(configured.allowed_origins, ())
        self.assertLessEqual(configured.default_page_size, configured.max_page_size)
        with self.assertRaises(FrozenInstanceError):
            configured.max_request_size = 0

    def test_every_integer_budget_rejects_bool_non_integer_and_zero(self):
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

    def test_keepalive_and_page_size_limits(self):
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

    def test_origins_require_explicit_http_authorities(self):
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

    def test_valid_origin_collection_is_copied_and_frozen(self):
        """Prevent a caller from expanding the trust boundary after validation.

        Returns
        -------
        None
            Confirm later caller mutations do not change allowed origins.
        """
        origins = ["https://example.com", "http://127.0.0.1:8000", "http://[::1]:8000"]
        configured = McpConfig(allowed_origins=origins)
        origins.append("https://evil.test")
        self.assertEqual(configured.allowed_origins, tuple(origins[:-1]))
