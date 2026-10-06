import importlib
import pkgutil
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from config.database import BootstrapDatabase
from config.http import BootstrapHTTP
from config.logging import BootstrapLogging
from config.mcp import BootstrapMcp
from config.realtime import BootstrapRealtime
from config.view import BootstrapView
from orionis.foundation.config.database import ConnectionName, Database
from orionis.foundation.config.http import (
    Cors, HTTPBodyLimits, HTTPRateLimit, HTTPWebSocket, Redis,
)
from orionis.foundation.config.logging import Logging
from orionis.foundation.config.mcp.entities.mcp import McpConfig
from orionis.foundation.config.realtime import RealtimeConfig
from orionis.foundation.config.view import View
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.body import BodyStream
from orionis.http.payload.stream_parser import MultipartStreamParser
from orionis.test import TestCase

if TYPE_CHECKING:
    from types import ModuleType

def configuration_modules() -> list[ModuleType]:
    """Load every configuration module, including public package reexports.

    Returns
    -------
    list[ModuleType]
        Value produced by the helper.
    """
    package = importlib.import_module("orionis.foundation.config")
    modules = [package]
    modules.extend(
        importlib.import_module(info.name)
        for info in pkgutil.walk_packages(package.__path__, package.__name__ + ".")
    )
    modules.extend(
        importlib.import_module("config." + path.stem)
        for path in sorted(Path("config").glob("*.py"))
    )
    return modules

def configuration_classes(modules: list[ModuleType]) -> list[type]:
    """Collect concrete dataclasses once, excluding imported aliases.

    Parameters
    ----------
    modules : list[ModuleType]
        Value supplied for ``modules``.

    Returns
    -------
    list[type]
        Value produced by the helper.
    """
    return [
        value
        for module in modules
        for value in vars(module).values()
        if isinstance(value, type)
        and is_dataclass(value)
        and value.__module__ == module.__name__
    ]

class EnvironmentDouble:
    """Provide deterministic environment values without writing to .env."""

    __slots__ = ("values", "writes")

    def __init__(self) -> None:
        """Create independently controlled values for each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.values: dict[str, object] = {}
        self.writes: list[tuple[str, object]] = []

    def get(self, key: str, default: object = None) -> object:
        """Return configured values, including explicit falsy values.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.
        default : object
            Value supplied for ``default``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self.values.get(key, default)

    def set(self, key: str, value: object) -> None:
        """Record a generated key without modifying process or disk state.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.
        value : object
            Value supplied for ``value``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.writes.append((key, value))

class ConfigurationTestCase(TestCase):
    """Isolate the environment consumed by all configuration factories."""

    def setUp(self) -> None:
        """Replace module environment references before each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.modules = configuration_modules()
        self.environment = EnvironmentDouble()
        self.originals = []
        for module in self.modules:
            if hasattr(module, "Env"):
                self.originals.append((module, module.Env))
                module.Env = self.environment

    def tearDown(self) -> None:
        """Restore all references even after failed configuration validation.

        Returns
        -------
        None
            Completes the operation described above.
        """
        for module, original in self.originals:
            module.Env = original

class TestConfigurationEnvironment(ConfigurationTestCase):
    def testSelectedDatabaseCharsetDoesNotInvalidateOtherConnections(self) -> None:
        """Keep backend-specific encodings out of inactive connection defaults.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.environment.values.update(DB_CONNECTION="mysql", DB_CHARSET="utf8mb4")
        for cls in (Database, BootstrapDatabase):
            with self.subTest(entity=cls.__name__):
                config = cls()
                self.assertEqual(config.connections.mysql.charset, "utf8mb4")
                self.assertEqual(config.connections.pgsql.charset, "UTF8")
        self.environment.values.update(
            DB_CONNECTION=ConnectionName.PGSQL,
            DB_CHARSET="LATIN1",
        )
        for cls in (Database, BootstrapDatabase):
            with self.subTest(entity=cls.__name__):
                self.assertEqual(cls().connections.pgsql.charset, "LATIN1")
                self.assertEqual(cls().connections.mysql.charset, "utf8mb4")

    def testSelectedStackPathDoesNotInvalidateRotatingChannels(self) -> None:
        """Use a plain stack filename while keeping valid rotation templates.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.environment.values.update(
            LOG_CHANNEL="stack",
            LOG_PATH="storage/custom.log",
        )
        for cls in (Logging, BootstrapLogging):
            with self.subTest(entity=cls.__name__):
                config = cls()
                self.assertEqual(config.channels.stack.path, "storage/custom.log")
                self.assertIn("{suffix}", config.channels.daily.path)

    def testSelectedRetentionIsValidatedForItsOwnTimeUnit(self) -> None:
        """Allow hourly retention above the unrelated monthly maximum.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.environment.values.update(LOG_CHANNEL="hourly", LOG_RETENTION=168)
        for cls in (Logging, BootstrapLogging):
            with self.subTest(entity=cls.__name__):
                self.assertEqual(cls().channels.hourly.retention_hours, 168)
                self.assertEqual(cls().channels.monthly.retention_months, 4)
        self.environment.values["LOG_RETENTION"] = 169
        for cls in (Logging, BootstrapLogging):
            with self.subTest(entity=cls.__name__), self.assertRaises(ValueError):
                cls()

    def testEnvironmentListsDoNotBecomeSharedInstanceDefaults(self) -> None:
        """Own collections even when the environment returns the same list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        values = ["https://example.com"]
        self.environment.values["CORS_ALLOW_ORIGINS"] = values
        first = Cors()
        second = Cors()
        first.allow_origins.clear()
        self.assertEqual(second.allow_origins, values)
        self.assertIsNot(second.allow_origins, values)

    def testEnvironmentFalsyValuesAreNotReplacedByDefaults(self) -> None:
        """Keep explicitly disabled template and bytecode caches.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.environment.values.update(
            VIEW_CACHE_SIZE=0,
            VIEW_AUTOESCAPE=False,
            APP_DEBUG=False,
            VIEW_CACHE_PATH=None,
        )
        for cls in (View, BootstrapView):
            with self.subTest(entity=cls.__name__):
                config = cls()
                self.assertEqual(config.cache_size, 0)
                self.assertFalse(config.autoescape)
                self.assertFalse(config.auto_reload)
                self.assertIsNone(config.cache_path)

class TestSharedRedisConfiguration(ConfigurationTestCase):
    """Keep shared Redis settings consistent without connecting to a server."""

    def testRateLimiterInheritsSharedConnectionSettings(self) -> None:
        """Use the same host, port, database and credential as other services.

        Returns
        -------
        None
            Core and application rate-limit configuration share connection fields.
        """
        credential = "test@credential:/?#%"
        self.environment.values.update({
            "REDIS_HOST": "cache.example", "REDIS_PORT": 6381,
            "REDIS_DB": 4, "REDIS_PASSWORD": credential,
        })
        for config in (HTTPRateLimit(), BootstrapHTTP().rate_limit):
            self.assertEqual(config.toDict()["rate_limit_redis"], {
                "endpoint": "cache.example", "port": 6381,
                "db": 4, "password": credential,
            })

    def testExplicitConnectionTakesPrecedenceWithoutReadingSharedValues(self) -> None:
        """Keep explicit Redis connection fields independent of shared defaults.

        Returns
        -------
        None
            An explicit connection wins even when unused shared data is invalid.
        """
        connection = Redis(
            endpoint="dedicated.example", port=6380, db=5, password=None,
        )
        self.environment.values.update(
            REDIS_HOST=None, REDIS_PORT="unused", REDIS_DB=-1, REDIS_PASSWORD=True,
        )
        core = HTTPRateLimit(rate_limit_redis=connection)
        bootstrap = BootstrapHTTP(rate_limit={"rate_limit_redis": connection})
        self.assertIs(core.rate_limit_redis, connection)
        self.assertIs(bootstrap.rate_limit.rate_limit_redis, connection)

    def testSharedIpv6HostRemainsLiteral(self) -> None:
        """Keep shared IPv6 addresses as raw client connection fields.

        Returns
        -------
        None
            Both configuration layers preserve the address and default port.
        """
        self.environment.values["REDIS_HOST"] = "::1"
        for config in (HTTPRateLimit(), BootstrapHTTP().rate_limit):
            connection = config.toDict()["rate_limit_redis"]
            self.assertEqual(connection["endpoint"], "::1")
            self.assertEqual(connection["port"], 6379)

    def testSharedDefaultsAndFalsyCredentialsArePreserved(self) -> None:
        """Keep the shared defaults, database zero and empty credentials intact.

        Returns
        -------
        None
            Verify both layers retain all four connection fields without a URL.
        """
        expected = {
            "endpoint": "127.0.0.1", "port": 6379, "db": 0, "password": None,
        }
        self.assertEqual(Redis().toDict(), expected)
        for config in (HTTPRateLimit(), BootstrapHTTP().rate_limit):
            self.assertEqual(config.toDict()["rate_limit_redis"], expected)
        self.environment.values.update(REDIS_DB=0, REDIS_PASSWORD="")
        expected["password"] = ""
        for config in (HTTPRateLimit(), BootstrapHTTP().rate_limit):
            self.assertEqual(config.toDict()["rate_limit_redis"], expected)

    def testSharedConnectionFactoriesReadEnvironmentLazily(self) -> None:
        """Read shared settings for each new immutable connection entity.

        Returns
        -------
        None
            Verify environment changes affect new connections, not earlier ones.
        """
        self.environment.values["REDIS_HOST"] = "first.cache"
        first = (HTTPRateLimit(), BootstrapHTTP().rate_limit)
        self.environment.values["REDIS_HOST"] = "second.cache"
        second = (HTTPRateLimit(), BootstrapHTTP().rate_limit)
        for before, after in zip(first, second, strict=True):
            self.assertEqual(
                before.toDict()["rate_limit_redis"]["endpoint"], "first.cache",
            )
            self.assertEqual(
                after.toDict()["rate_limit_redis"]["endpoint"], "second.cache",
            )
            self.assertIsNot(before.rate_limit_redis, after.rate_limit_redis)

class TestRealtimeConfigurationEnvironment(ConfigurationTestCase):
    def testDefaultsMatchStaticMetadata(self) -> None:
        """Keep realtime defaults and their descriptive metadata aligned.

        Returns
        -------
        None
            Verify all seven defaults in both configuration layers.
        """
        expected = {
            "max_message_size": 1048576,
            "max_concurrent_invocations": 16,
            "max_pending_client_invocations": 32,
            "invocation_timeout": 30.0,
            "client_result_timeout": 30.0,
            "broadcast_concurrency": 32,
            "max_groups_per_connection": 64,
        }
        self.assertEqual(RealtimeConfig().toDict(), expected)
        self.assertEqual(BootstrapRealtime().toDict(), expected)
        self.assertEqual(set(BootstrapRealtime.__annotations__), set(expected))
        for item in fields(RealtimeConfig):
            with self.subTest(field=item.name):
                self.assertEqual(item.metadata["default"], expected[item.name])
                self.assertTrue(item.metadata["description"])

    def testEnvironmentIsReadForEveryNewInstance(self) -> None:
        """Read current environment values without changing static metadata.

        Returns
        -------
        None
            Verify lazy reads and explicit overrides in both layers.
        """
        for cls in (RealtimeConfig, BootstrapRealtime):
            for item in fields(RealtimeConfig):
                key = "REALTIME_" + item.name.upper()
                default = item.metadata["default"]
                with self.subTest(entity=cls.__name__, field=item.name):
                    self.environment.values[key] = default + 1
                    first = cls()
                    self.assertEqual(getattr(first, item.name), default + 1)
                    self.environment.values[key] = default + 2
                    self.assertEqual(getattr(cls(), item.name), default + 2)
                    self.assertEqual(getattr(first, item.name), default + 1)
                    explicit = cls(**{item.name: default})
                    self.assertEqual(getattr(explicit, item.name), default)
                    self.assertEqual(item.metadata["default"], default)

    def testInvalidEnvironmentBudgetsRemainRejected(self) -> None:
        """Validate environment budgets through the existing entity checks.

        Returns
        -------
        None
            Reject booleans, nonpositive budgets and nonfinite timeouts.
        """
        for cls in (RealtimeConfig, BootstrapRealtime):
            for item in fields(RealtimeConfig):
                key = "REALTIME_" + item.name.upper()
                for value, error in (
                    (True, TypeError), (0, ValueError), (-1, ValueError),
                ):
                    self.environment.values.clear()
                    self.environment.values[key] = value
                    with self.subTest(
                        entity=cls.__name__, field=item.name, value=value,
                    ), self.assertRaises(error):
                        cls()
            for name in ("invocation_timeout", "client_result_timeout"):
                for value in (float("inf"), float("nan")):
                    self.environment.values.clear()
                    self.environment.values["REALTIME_" + name.upper()] = value
                    with self.subTest(
                        entity=cls.__name__, field=name, value=value,
                    ), self.assertRaises(ValueError):
                        cls()

class TestProtocolEnvironment(ConfigurationTestCase):
    """Keep protocol defaults environment-backed and their origins explicit."""

    def testProtocolFieldsDeclareStaticDefaultsAndDescriptions(self) -> None:
        """Keep protocol metadata aligned with the documented fallback values.

        Returns
        -------
        None
            Every field exposes a static default and a nonempty description.
        """
        expected = (
            (HTTPWebSocket, {
                "max_connections": 128,
                "max_message_size": 1024 * 1024,
                "allow_origins": (),
            }),
            (McpConfig, {
                "max_request_size": 1024 * 1024,
                "default_page_size": 50,
                "max_page_size": 100,
                "max_concurrent_requests": 32,
                "subscription_buffer_size": 64,
                "max_subscriptions": 1024,
                "max_resource_subscriptions": 64,
                "subscription_keepalive": 15.0,
                "allowed_origins": (),
                "tool_search_max_results": 20,
                "tool_search_max_calls": 5,
                "tool_search_max_output_bytes": 256 * 1024,
                "max_response_size": 4 * 1024 * 1024,
                "max_metadata_size": 64 * 1024,
            }),
        )
        for config_type, defaults in expected:
            self.assertEqual(config_type().toDict(), defaults)
            for item in fields(config_type):
                with self.subTest(entity=config_type.__name__, field=item.name):
                    self.assertEqual(item.metadata["default"], defaults[item.name])
                    self.assertTrue(item.metadata["description"])

    def testEveryMcpBudgetReadsEnvironmentForEachInstance(self) -> None:
        """Read all MCP budgets lazily while retaining immutable instances.

        Returns
        -------
        None
            Environment changes affect new configurations, not previous ones.
        """
        for config_type in (McpConfig, BootstrapMcp):
            for item in fields(McpConfig):
                if item.name == "allowed_origins":
                    continue
                self.environment.values.clear()
                default = getattr(config_type(), item.name)
                key = "MCP_" + item.name.upper()
                self.environment.values[key] = default + 1
                first = config_type()
                self.assertEqual(getattr(first, item.name), default + 1)
                self.environment.values[key] = default + 2
                self.assertEqual(getattr(config_type(), item.name), default + 2)
                self.assertEqual(getattr(first, item.name), default + 1)

    def testMcpInheritsSharedHttpBudgetsUnlessOverridden(self) -> None:
        """Apply shared HTTP defaults with explicit MCP override precedence.

        Returns
        -------
        None
            Request bytes and concurrent admission can share HTTP environment values.
        """
        self.environment.values.update(
            HTTP_MAX_BODY_SIZE=2048, HTTP_MAX_CONCURRENT_REQUESTS=8,
        )
        for config_type in (McpConfig, BootstrapMcp):
            self.assertEqual(config_type().max_request_size, 2048)
            self.assertEqual(config_type().max_concurrent_requests, 8)
        self.environment.values.update(
            MCP_MAX_REQUEST_SIZE=512, MCP_MAX_CONCURRENT_REQUESTS=2,
        )
        self.assertEqual(McpConfig().max_request_size, 512)
        self.assertEqual(McpConfig().max_concurrent_requests, 2)

    def testSharedOriginsUseOnlyCorsVariable(self) -> None:
        """Read one shared origin variable without protocol-specific overrides.

        Returns
        -------
        None
            Core and bootstrap configurations use the same CORS origin values.
        """
        origins = ["https://client.example", "http://localhost:3000"]
        self.environment.values.update(
            CORS_ALLOW_ORIGINS=origins,
            MCP_ALLOWED_ORIGINS=["https://mcp-only.example"],
            WEBSOCKET_ALLOW_ORIGINS=["https://websocket-only.example"],
        )
        expected = tuple(origins)
        self.assertEqual(McpConfig().allowed_origins, expected)
        self.assertEqual(BootstrapMcp().allowed_origins, expected)
        self.assertEqual(HTTPWebSocket().allow_origins, expected)
        self.assertEqual(BootstrapHTTP().websocket.allow_origins, expected)

    def testSharedOriginsAreReadLazilyAndFrozen(self) -> None:
        """Read shared defaults for new instances without sharing mutable lists.

        Returns
        -------
        None
            Verify empty defaults and preserve earlier origin snapshots.
        """
        self.assertEqual(McpConfig().allowed_origins, ())
        self.assertEqual(BootstrapMcp().allowed_origins, ())
        self.assertEqual(HTTPWebSocket().allow_origins, ())
        self.assertEqual(BootstrapHTTP().websocket.allow_origins, ())
        origins = ["https://first.example"]
        self.environment.values["CORS_ALLOW_ORIGINS"] = origins
        first = (
            McpConfig().allowed_origins, BootstrapMcp().allowed_origins,
            HTTPWebSocket().allow_origins, BootstrapHTTP().websocket.allow_origins,
        )
        origins[0] = "https://second.example"
        second = (
            McpConfig().allowed_origins, BootstrapMcp().allowed_origins,
            HTTPWebSocket().allow_origins, BootstrapHTTP().websocket.allow_origins,
        )
        self.assertEqual(first, (("https://first.example",),) * 4)
        self.assertEqual(second, (("https://second.example",),) * 4)

    def testExplicitProtocolOriginsCanDifferFromSharedDefaults(self) -> None:
        """Leave separately supplied origins under the developer's control.

        Returns
        -------
        None
            Verify explicit constructor values override only their own protocol.
        """
        self.environment.values["CORS_ALLOW_ORIGINS"] = ["https://shared.example"]
        origins = ("https://private.example",)
        self.assertEqual(McpConfig(allowed_origins=origins).allowed_origins, origins)
        self.assertEqual(BootstrapMcp(allowed_origins=origins).allowed_origins, origins)
        self.assertEqual(HTTPWebSocket(allow_origins=origins).allow_origins, origins)
        config = BootstrapHTTP(websocket={"allow_origins": origins})
        self.assertEqual(config.websocket.allow_origins, origins)
        self.assertEqual(config.cors.allow_origins, ["https://shared.example"])

    def testInvalidSharedOriginsRemainRejected(self) -> None:
        """Validate the shared variable through each existing protocol entity.

        Returns
        -------
        None
            Reject malformed origin collections and invalid entries.
        """
        for origins in ("https://client.example", None, [1], [" "]):
            self.environment.values["CORS_ALLOW_ORIGINS"] = origins
            for config_type in (
                McpConfig, BootstrapMcp, HTTPWebSocket, BootstrapHTTP,
            ):
                with self.subTest(
                    entity=config_type.__name__, origins=origins,
                ), self.assertRaises((TypeError, ValueError)):
                    config_type()

    def testSharedWildcardsFollowEachProtocolValidation(self) -> None:
        """Do not silently filter the shared origin values before validation.

        Returns
        -------
        None
            WebSocket retains wildcard values while MCP rejects them.
        """
        for origins in (["*"], ["https://*.example.com"]):
            self.environment.values["CORS_ALLOW_ORIGINS"] = origins
            for config_type in (McpConfig, BootstrapMcp):
                with self.subTest(
                    entity=config_type.__name__, origins=origins,
                ), self.assertRaises(ValueError):
                    config_type()
            expected = tuple(origins)
            self.assertEqual(HTTPWebSocket().allow_origins, expected)
            self.assertEqual(BootstrapHTTP().websocket.allow_origins, expected)

    def testCoreWebSocketConfigurationReadsItsEnvironment(self) -> None:
        """Apply the same WebSocket budgets in the core and application layers.

        Returns
        -------
        None
            Both layers consume the declared connection and message limits.
        """
        self.environment.values.update(
            WEBSOCKET_MAX_CONNECTIONS=12, WEBSOCKET_MAX_MESSAGE_SIZE=8192,
        )
        for config in (HTTPWebSocket(), BootstrapHTTP().websocket):
            self.assertEqual(config.max_connections, 12)
            self.assertEqual(config.max_message_size, 8192)

class TestHttpBodyLimitsEnvironment(ConfigurationTestCase):
    """Keep core and application request budgets consistent with the environment."""

    def testBodyFieldsDeclareStaticDefaultsAndDescriptions(self) -> None:
        """Expose descriptive metadata for every finite request budget.

        Returns
        -------
        None
            Core defaults, application defaults and static metadata agree.
        """
        expected = {
            "max_body_size": 16 * 1024 * 1024,
            "max_buffer_size": 2 * 1024 * 1024,
            "max_concurrent_requests": 128,
            "max_files": 32,
            "max_fields": 128,
            "max_part_size": 10 * 1024 * 1024,
            "max_field_size": 1024 * 1024,
            "max_header_size": 16 * 1024,
            "memory_threshold": 256 * 1024,
            "max_memory_size": 8 * 1024 * 1024,
        }
        self.assertEqual(HTTPBodyLimits().toDict(), expected)
        self.assertEqual(BootstrapHTTP().body_limits.toDict(), expected)
        for item in fields(HTTPBodyLimits):
            with self.subTest(field=item.name):
                self.assertEqual(item.metadata["default"], expected[item.name])
                self.assertTrue(item.metadata["description"])

    def testBodyLimitsReadEnvironmentLazilyAndPreserveExplicitValues(self) -> None:
        """Read each existing HTTP key only for new defaulted configurations.

        Returns
        -------
        None
            Environment changes leave earlier snapshots and explicit limits intact.
        """
        keys = {
            "max_header_size": "HTTP_MAX_PART_HEADER_SIZE",
            "memory_threshold": "HTTP_UPLOAD_MEMORY_THRESHOLD",
            "max_memory_size": "HTTP_MAX_MULTIPART_MEMORY_SIZE",
        }
        for item in fields(HTTPBodyLimits):
            self.environment.values.clear()
            default = getattr(HTTPBodyLimits(), item.name)
            key = keys.get(item.name, "HTTP_" + item.name.upper())
            self.environment.values[key] = default + 1
            first = HTTPBodyLimits()
            self.assertEqual(getattr(first, item.name), default + 1)
            self.assertEqual(
                getattr(BootstrapHTTP().body_limits, item.name), default + 1,
            )
            self.environment.values[key] = default + 2
            self.assertEqual(getattr(HTTPBodyLimits(), item.name), default + 2)
            self.assertEqual(getattr(first, item.name), default + 1)
            self.environment.values[key] = None
            explicit = HTTPBodyLimits(**{item.name: default})
            self.assertEqual(getattr(explicit, item.name), default)
            self.assertEqual(item.metadata["default"], default)

    def testBodyEnvironmentValidationKeepsFiniteBudgetsAndZeroCounts(self) -> None:
        """Reject invalid environment limits while allowing uploads to be disabled.

        Returns
        -------
        None
            Counts accept zero; every limit rejects booleans and invalid types.
        """
        keys = {
            "max_header_size": "HTTP_MAX_PART_HEADER_SIZE",
            "memory_threshold": "HTTP_UPLOAD_MEMORY_THRESHOLD",
            "max_memory_size": "HTTP_MAX_MULTIPART_MEMORY_SIZE",
        }
        for item in fields(HTTPBodyLimits):
            key = keys.get(item.name, "HTTP_" + item.name.upper())
            for value, error in (
                (True, TypeError), (False, TypeError), (1.5, TypeError),
                ("invalid", TypeError), (None, TypeError), (-1, ValueError),
            ):
                self.environment.values.clear()
                self.environment.values[key] = value
                with self.subTest(field=item.name, value=value):
                    with self.assertRaises(error):
                        HTTPBodyLimits()
                    with self.assertRaises(error):
                        BootstrapHTTP()
            self.environment.values[key] = 0
            if item.name in ("max_files", "max_fields"):
                self.assertEqual(getattr(HTTPBodyLimits(), item.name), 0)
                self.assertEqual(getattr(BootstrapHTTP().body_limits, item.name), 0)
            else:
                with self.assertRaises(ValueError):
                    HTTPBodyLimits()
                with self.assertRaises(ValueError):
                    BootstrapHTTP()

    def testMultipartValidationDoesNotReadUnusedEnvironmentLimits(self) -> None:
        """Keep manual multipart parsing independent of unrelated HTTP budgets.

        Returns
        -------
        None
            Parser defaults and explicit values bypass unused environment limits.
        """
        self.environment.values.update(
            HTTP_MAX_BUFFER_SIZE=None, HTTP_MAX_CONCURRENT_REQUESTS=None,
        )
        with self.assertRaises(TypeError):
            HTTPBodyLimits()
        parser = MultipartStreamParser(
            BodyStream(Interface.ASGI, None).stream(), b"body-limits",
            max_body_size=512, max_files=0,
        )
        self.assertEqual(parser.max_body_size, 512)
        self.assertEqual(parser.max_files, 0)
        self.assertEqual(parser.max_fields, 128)
