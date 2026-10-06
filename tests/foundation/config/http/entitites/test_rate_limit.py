from orionis.foundation.config.http import HTTP, HTTPRateLimit, Redis
from orionis.test import TestCase

class TestHTTPRateLimitConfig(TestCase):
    """Validate bounded capacities and optional distributed transport settings."""

    def testRoundTripsConfiguredRedisBackendThroughHTTP(self) -> None:
        """Preserve Redis settings when HTTP coerces a plain dictionary.

        Returns
        -------
        None
            Verify configured settings survive HTTP serialization.
        """
        connection = {
            "endpoint": "::1",
            "port": 6381,
            "db": 4,
            "password": "test@credential:/?#%",
        }
        config = HTTP(rate_limit={
            "rate_limit_store": "redis",
            "rate_limit_max_keys": 20,
            "rate_limit_max_events": 50,
            "rate_limit_redis": connection,
            "rate_limit_redis_prefix": "my-app:rate-limit",
            "rate_limit_redis_timeout_seconds": 2,
        }).toDict()["rate_limit"]
        self.assertEqual(config["rate_limit_store"], "redis")
        self.assertEqual(config["rate_limit_max_keys"], 20)
        self.assertEqual(config["rate_limit_max_events"], 50)
        self.assertEqual(config["rate_limit_redis"], connection)
        self.assertEqual(config["rate_limit_redis_prefix"], "my-app:rate-limit")

    def testPreservesExplicitRedisConnection(self) -> None:
        """Accept an immutable Redis entity without replacing it.

        Returns
        -------
        None
            Verify explicit connection settings survive nested serialization.
        """
        connection = Redis(endpoint="cache.example", port=6381, db=4, password=None)
        config = HTTPRateLimit(rate_limit_redis=connection)
        self.assertIs(config.rate_limit_redis, connection)
        self.assertEqual(config.toDict()["rate_limit_redis"], connection.toDict())
        self.assertNotIn("rate_limit_redis_url", config.toDict())

    def testRejectsInvalidBackendConfiguration(self) -> None:
        """Reject unsupported backends and unsafe capacity or timeout values.

        Returns
        -------
        None
            Verify invalid rate-limit settings fail validation.
        """
        invalid = (
            {"rate_limit_store": "database"},
            {"rate_limit_store": True},
            {"rate_limit_max_keys": 0},
            {"rate_limit_max_events": -1},
            {"rate_limit_max_events": True},
            {"rate_limit_redis": "redis://localhost/0"},
            {"rate_limit_redis": None},
            {"rate_limit_redis": {"endpoint": " "}},
            {"rate_limit_redis": {"endpoint": None}},
            {"rate_limit_redis": {"port": 0}},
            {"rate_limit_redis": {"port": 65536}},
            {"rate_limit_redis": {"port": True}},
            {"rate_limit_redis": {"db": -1}},
            {"rate_limit_redis": {"db": True}},
            {"rate_limit_redis": {"password": True}},
            {"rate_limit_redis_prefix": " "},
            {"rate_limit_redis_timeout_seconds": 0},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(
                (TypeError, ValueError),
            ):
                HTTPRateLimit(**values)
