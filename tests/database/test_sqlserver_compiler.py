"""SQL Server compilation regressions confirmed by private database tests."""

from sqlalchemy.dialects import mssql
from orionis.database.compiler import SQLCompiler
from orionis.orm.query.expressions import LockMode, SelectPlan
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer
from orionis.test import TestCase


class TestSQLServerCompiler(TestCase):
    def definition(self, *, incrementing: bool = False) -> TableDefinition:
        """
        Build a schema-qualified table with explicit key generation.

        Parameters
        ----------
        incrementing : bool, optional
            Enable automatic primary key generation; default to False.

        Returns
        -------
        TableDefinition
            The users table in the owned schema with an integer primary key.
        """
        column = Integer().primary()
        if incrementing:
            column.autoIncrement()
        column.name = "id"
        return TableDefinition(name="users", schema="owned", columns={"id": column})

    def testClientManagedIntegerPrimaryKeyDoesNotBecomeIdentity(self) -> None:
        """
        Verify that client-managed SQL Server keys omit identity generation.

        Returns
        -------
        None
            Assert that compiled table DDL contains no identity clause.
        """
        ddl = str(SQLCompiler(driver="sqlserver").compileCreateTable(
            self.definition(),
        ).compile(dialect=mssql.dialect()))
        self.assertNotIn("IDENTITY", ddl.upper())

    def testExplicitAutoIncrementIntegerPrimaryKeyRetainsIdentity(self) -> None:
        """
        Verify that explicit auto-increment keys retain SQL Server identity.

        Returns
        -------
        None
            Assert that compiled table DDL includes an identity clause.
        """
        ddl = str(SQLCompiler(driver="sqlserver").compileCreateTable(
            self.definition(incrementing=True),
        ).compile(dialect=mssql.dialect()))
        self.assertIn("IDENTITY", ddl.upper())

    def testUpdateLockUsesSqlServerHintOnAliasedTable(self) -> None:
        """
        Verify that update lock hints apply to aliased SQL Server tables.

        Returns
        -------
        None
            Assert that the compiled query includes UPDLOCK and ROWLOCK hints.
        """
        statement = SQLCompiler(driver="sqlserver").compileSelect(
            SelectPlan(table=self.definition(), alias="u", lock=LockMode.UPDATE),
        )
        sql = str(statement.compile(dialect=mssql.dialect()))
        self.assertIn("WITH (UPDLOCK, ROWLOCK)", sql)

    def testSharedLockUsesSqlServerHintOnQualifiedTable(self) -> None:
        """
        Verify that shared lock hints apply to schema-qualified tables.

        Returns
        -------
        None
            Assert that the compiled query includes HOLDLOCK and ROWLOCK hints.
        """
        statement = SQLCompiler(driver="sqlserver").compileSelect(
            SelectPlan(table=self.definition(), lock=LockMode.SHARE),
        )
        self.assertIn("WITH (HOLDLOCK, ROWLOCK)", str(statement.compile(
            dialect=mssql.dialect(),
        )))
