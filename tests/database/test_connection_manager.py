from __future__ import annotations
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection import IConnection
from orionis.database.exceptions import ConnectionNotFoundException
from orionis.test import TestCase

class _StubApp:
    """Minimal application stub exposing the database configuration."""

    def __init__(self, config: dict) -> None:
        """Initialize the test double.

        Parameters
        ----------
        config : dict
            Value supplied for ``config``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._config = config

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Return the requested database configuration.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return self._config

def _makeManager() -> ConnectionManager:
    """Build a manager with two in-memory sqlite connections.

    Returns
    -------
    ConnectionManager
        Value produced by the helper.
    """
    return ConnectionManager(_StubApp({
        "default": "sqlite",
        "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:", "prefix": ""},
            "replica": {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        },
    }))

class TestConnectionManager(TestCase):

    def setUp(self) -> None:
        """Create a fresh manager before each test.

        Guarantees isolation of the connection cache.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._manager = _makeManager()

    async def asyncTearDown(self) -> None:
        """Dispose every cached connection after each test.

        Releases pooled resources between tests.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self._manager.disconnect()

    # ── Resolution ────────────────────────────────────────────────────────────

    def testConnectionResolvesDefault(self) -> None:
        """Resolve the default connection when no name is given.

        Validates default connection resolution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        connection = self._manager.connection()
        self.assertIsInstance(connection, IConnection)
        self.assertEqual(connection.getName(), "sqlite")

    def testConnectionResolvesNamed(self) -> None:
        """Resolve a named connection from the configuration.

        Validates named connection resolution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        connection = self._manager.connection("replica")
        self.assertEqual(connection.getName(), "replica")

    def testConnectionIsCachedPerName(self) -> None:
        """Cache connections so repeated access returns the same object.

        Validates the identity of cached connections.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        first = self._manager.connection()
        second = self._manager.connection("sqlite")
        self.assertIs(first, second)

    def testUnknownConnectionRaises(self) -> None:
        """Raise ConnectionNotFoundException for unregistered names.

        Validates the descriptive resolution failure.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ConnectionNotFoundException):
            self._manager.connection("missing")

    # ── Registration ──────────────────────────────────────────────────────────

    def testAddConnectionRegistersConfiguration(self) -> None:
        """Register a new connection configuration at runtime.

        Validates the runtime registration entry point.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self._manager.addConnection(
            "runtime",
            {"driver": "sqlite", "database": ":memory:"},
        )
        self.assertTrue(self._manager.hasConnection("runtime"))
        self.assertEqual(
            self._manager.connection("runtime").getName(),
            "runtime",
        )

    def testAddConnectionValidatesArguments(self) -> None:
        """Reject empty names and non-mapping configurations.

        Validates the registration guards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            self._manager.addConnection("", {})
        with self.assertRaises(TypeError):
            self._manager.addConnection("bad", "not-a-dict")

    # ── Default connection ────────────────────────────────────────────────────

    def testDefaultNameAccessors(self) -> None:
        """Read and change the default connection name.

        Validates the default-name accessors and their guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(self._manager.getDefaultName(), "sqlite")
        self._manager.setDefaultName("replica")
        self.assertEqual(self._manager.connection().getName(), "replica")
        with self.assertRaises(ConnectionNotFoundException):
            self._manager.setDefaultName("missing")

    # ── Configuration lookup ──────────────────────────────────────────────────

    def testConfigForReturnsNamedConfiguration(self) -> None:
        """Retrieve the raw configuration for a named connection.

        Validates the configFor lookup used outside connection building.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        config = self._manager.configFor("replica")
        self.assertEqual(config["driver"], "sqlite")

    def testConfigForDefaultsToDefaultConnection(self) -> None:
        """Retrieve the default connection configuration without a name.

        Validates the same default-resolution rule used by connection().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            self._manager.configFor(),
            self._manager.configFor("sqlite"),
        )

    def testConfigForUnknownConnectionRaises(self) -> None:
        """Raise ConnectionNotFoundException for unregistered names.

        Validates that configFor fails the same way as connection().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ConnectionNotFoundException):
            self._manager.configFor("missing")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def testDisconnectRemovesCachedConnection(self) -> None:
        """Dispose a named connection and drop it from the cache.

        Validates that a fresh instance is built afterwards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        first = self._manager.connection()
        await self._manager.disconnect("sqlite")
        second = self._manager.connection()
        self.assertIsNot(first, second)

    async def testDisconnectAllClearsEveryCachedConnection(self) -> None:
        """Dispose every cached connection when no name is given.

        Validates the bulk-disconnect branch of the lifecycle method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        first_default = self._manager.connection()
        first_replica = self._manager.connection("replica")
        await self._manager.disconnect()
        second_default = self._manager.connection()
        second_replica = self._manager.connection("replica")
        self.assertIsNot(first_default, second_default)
        self.assertIsNot(first_replica, second_replica)

    async def testDisconnectUnknownNameIsNoOp(self) -> None:
        """Do nothing when disconnecting a name that was never resolved.

        Validates that disconnect is safe to call for untouched names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self._manager.disconnect("never-touched")
