from __future__ import annotations
from orionis.foundation.config.database.entities.connections import Connections
from orionis.foundation.config.database.entities.database import Database
from orionis.foundation.config.database.entities.sqlserver import SQLServer
from orionis.test import TestCase

class TestSQLServerEntity(TestCase):

    def testDefaultsAreValid(self) -> None:
        """Build the entity with its default values.

        Only the driver discriminator is pinned to a literal: every
        other field falls back to a ``DB_*`` environment variable, so
        asserting them would make the test depend on the machine.

        Validates the default SQL Server configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SQLServer()
        self.assertEqual(entity.driver, "sqlserver")
        self.assertIsInstance(entity.port, int)
        self.assertIsInstance(entity.username, str)
        self.assertIsInstance(entity.odbc_driver, str)

    def testExplicitValuesAreHonored(self) -> None:
        """Keep explicitly supplied values untouched.

        Validates that the environment fallback never overrides an
        explicit value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SQLServer(port=1433, username="sa")
        self.assertEqual(entity.port, 1433)
        self.assertEqual(entity.username, "sa")

    def testInvalidDriverRaises(self) -> None:
        """Reject entities with a wrong driver discriminator.

        Validates the driver guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            SQLServer(driver="mssql")

    def testInvalidPortRaises(self) -> None:
        """Reject out-of-range and non-integer ports.

        Validates the endpoint guards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            SQLServer(port=0)
        with self.assertRaises(TypeError):
            SQLServer(port="1433")

    def testInvalidHostAndDatabaseRaise(self) -> None:
        """Reject empty host and database names.

        Validates the endpoint guards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            SQLServer(host="")
        with self.assertRaises(ValueError):
            SQLServer(database="")

    def testInvalidCredentialsRaise(self) -> None:
        """Reject empty usernames and non-string passwords.

        Validates the credential guards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            SQLServer(username="")
        with self.assertRaises(TypeError):
            SQLServer(password=123)

    def testInvalidOdbcDriverRaises(self) -> None:
        """Reject empty ODBC driver names.

        Validates the driver option guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            SQLServer(odbc_driver="")

class TestConnectionsWithSqlServer(TestCase):

    def testConnectionsExposeSqlServerEntry(self) -> None:
        """Expose a sqlserver entry converted to its entity.

        Validates the Connections integration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        connections = Connections()
        self.assertIsInstance(connections.sqlserver, SQLServer)

        from_dict = Connections(sqlserver={"driver": "sqlserver"})
        self.assertIsInstance(from_dict.sqlserver, SQLServer)

    def testDatabaseAcceptsSqlServerAsDefault(self) -> None:
        """Accept 'sqlserver' as the default connection name.

        Validates the Database entity validation set.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        database = Database(default="sqlserver")
        self.assertEqual(database.default, "sqlserver")

    def testConnectionsRejectInvalidSqlServerType(self) -> None:
        """Reject sqlserver values that are neither entity nor dict.

        Validates the table-driven type validation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Connections(sqlserver=42)
