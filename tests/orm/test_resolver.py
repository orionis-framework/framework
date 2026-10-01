from __future__ import annotations
from orionis.database.connection_manager import ConnectionManager
from orionis.database.exceptions import ConnectionNotFoundException
from orionis.orm.exceptions import OrmConfigurationException
from orionis.orm.resolver import ConnectionResolver
from orionis.test import TestCase

class _StubApp:
    """Minimal application stub exposing the database configuration."""

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Run the config helper.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }

class TestConnectionResolver(TestCase):
    def setUp(self) -> None:
        """Snapshot the globally installed manager before each test.

        Allows restoring the application wiring afterwards.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._previous = ConnectionResolver._manager

    def tearDown(self) -> None:
        """Restore the globally installed manager after each test.

        Keeps the application wiring intact for other suites.

        Returns
        -------
        None
            Completes the operation described above.
        """
        ConnectionResolver._manager = self._previous

    def testManagerRaisesWhenUnset(self) -> None:
        """Raise OrmConfigurationException before wiring the manager.

        Validates the descriptive unset-resolver failure.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ConnectionResolver.clear()
        with self.assertRaises(OrmConfigurationException):
            ConnectionResolver.manager()
        with self.assertRaises(OrmConfigurationException):
            ConnectionResolver.connection()

    def testSetManagerInstallsAndResolves(self) -> None:
        """Install a manager and resolve connections through it.

        Validates the static bridge used by every model.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(manager)
        self.assertIs(ConnectionResolver.manager(), manager)
        self.assertEqual(
            ConnectionResolver.connection().getName(),
            "sqlite",
        )
        self.assertEqual(
            ConnectionResolver.connection("sqlite").getName(),
            "sqlite",
        )

    def testClearRemovesManager(self) -> None:
        """Remove the installed manager with clear().

        Validates the test isolation helper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ConnectionResolver.setManager(ConnectionManager(_StubApp()))
        ConnectionResolver.clear()
        with self.assertRaises(OrmConfigurationException):
            ConnectionResolver.manager()

    def testConnectionPropagatesUnknownNameError(self) -> None:
        """Propagate the manager's error for an unregistered connection.

        Validates that the resolver delegates without swallowing the
        manager's own connection-resolution failures.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ConnectionResolver.setManager(ConnectionManager(_StubApp()))
        with self.assertRaises(ConnectionNotFoundException):
            ConnectionResolver.connection("missing")
