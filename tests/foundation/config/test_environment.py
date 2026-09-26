from config.database import BootstrapDatabase
from config.logging import BootstrapLogging
from config.view import BootstrapView
from orionis.foundation.config.database import ConnectionName, Database
from orionis.foundation.config.http import Cors
from orionis.foundation.config.logging import Logging
from orionis.foundation.config.view import View
from tests.foundation.config.support import ConfigurationTestCase


class TestConfigurationEnvironment(ConfigurationTestCase):
    def testSelectedDatabaseCharsetDoesNotInvalidateOtherConnections(self) -> None:
        """Keep backend-specific encodings out of inactive connection defaults."""
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
        """Use a plain stack filename while keeping valid rotation templates."""
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
        """Allow hourly retention above the unrelated monthly maximum."""
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
        """Own collections even when the environment returns the same list."""
        values = ["https://example.com"]
        self.environment.values["CORS_ALLOW_ORIGINS"] = values
        first = Cors()
        second = Cors()
        first.allow_origins.clear()
        self.assertEqual(second.allow_origins, values)
        self.assertIsNot(second.allow_origins, values)

    def testEnvironmentFalsyValuesAreNotReplacedByDefaults(self) -> None:
        """Keep explicitly disabled template and bytecode caches."""
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
