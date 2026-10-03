import importlib
import pkgutil
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from config.database import BootstrapDatabase
from config.logging import BootstrapLogging
from config.realtime import BootstrapRealtime
from config.view import BootstrapView
from orionis.foundation.config.database import ConnectionName, Database
from orionis.foundation.config.http import Cors
from orionis.foundation.config.logging import Logging
from orionis.foundation.config.realtime import RealtimeConfig
from orionis.foundation.config.view import View
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
