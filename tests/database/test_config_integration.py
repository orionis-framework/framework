from __future__ import annotations
from unittest.mock import patch
from config.database import BootstrapDatabase
from orionis.database.connection_manager import ConnectionManager
from orionis.database.dialect import (
    build_engine_url,
    engine_options,
    resolve_driver,
)
from orionis.foundation.config.database.entities.database import Database
from orionis.test import TestCase

# Every first-party connection declared by the configuration entities.
_EXPECTED_CONNECTIONS = ("sqlite", "mysql", "pgsql", "oracle", "sqlserver")


def template_config() -> dict:
    """Build the application database template with its documented defaults."""
    with patch("config.database.Env") as environment:
        environment.get.side_effect = lambda _key, default=None: default
        return BootstrapDatabase().toDict()


class _EntityStubApp:
    """Application stub returning the Database entity (not a dict)."""

    def config(self, key: str) -> Database:  # noqa: ARG002
        return Database()

class TestConfigurationContract(TestCase):

    def testEveryDefaultConnectionSpeaksWithTheDialect(self) -> None:
        """
        Run every default connection entity through the dialect layer.

        Validates that each configuration produced by the entities is
        fully understood: driver resolution, URL building, and engine
        options never fail and target the expected dialect.
        """
        config = Database().toDict()
        connections = config["connections"]

        for name in _EXPECTED_CONNECTIONS:
            self.assertIn(name, connections)
            entry = connections[name]
            self.assertEqual(resolve_driver(entry), name)
            url = build_engine_url(entry)
            self.assertTrue(url.drivername)
            options = engine_options(entry)
            self.assertIn("future", options)

    def testDefaultConnectionNameIsDeclared(self) -> None:
        """
        Keep the default connection inside the declared connections.

        Validates the default/connections coherence of the entity.
        """
        config = Database().toDict()
        self.assertIn(config["default"], config["connections"])

    def testManagerConsumesEntityConfiguration(self) -> None:
        """
        Build the manager from the entity object instead of a dict.

        Validates the entity normalization path used when the runtime
        configuration returns dataclass instances.
        """
        manager = ConnectionManager(_EntityStubApp())
        for name in _EXPECTED_CONNECTIONS:
            self.assertTrue(manager.hasConnection(name))
        self.assertEqual(
            manager.connection().getName(),
            manager.getDefaultName(),
        )

    def testApplicationTemplateConfigSpeaksWithTheDialect(self) -> None:
        """
        Validate the application database template against every dialect.

        Every connection declared by ``config/database.py`` must resolve
        its driver and build a valid engine URL with engine options.
        """
        config = template_config()

        connections = config.get("connections", {})
        self.assertIn(config.get("default"), connections)

        for name in _EXPECTED_CONNECTIONS:
            self.assertIn(name, connections)
            entry = connections[name]
            entry = entry if isinstance(entry, dict) else entry.toDict()
            self.assertEqual(resolve_driver(entry), name)
            self.assertTrue(build_engine_url(entry).drivername)
            engine_options(entry)

    def testApplicationSqliteUrlAndDatabaseAreCoherent(self) -> None:
        """
        Keep the sqlite informational URL aligned with the database path.

        Validates that the app template derives both values from the
        same source, avoiding split-brain configuration.
        """
        config = template_config()
        sqlite = config["connections"]["sqlite"]
        sqlite = sqlite if isinstance(sqlite, dict) else sqlite.toDict()

        url = str(sqlite.get("url", ""))
        database = str(sqlite.get("database", ""))
        if url.startswith("sqlite:///"):
            self.assertTrue(url.endswith(database))
