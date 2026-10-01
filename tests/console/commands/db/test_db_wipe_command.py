import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from orionis.console.commands.db._inspection import DatabaseInspector
from orionis.console.commands.db.wipe import DatabaseWiper, DbWipeCommand
from orionis.database.connection_manager import ConnectionManager
from orionis.test import TestCase

class _ConfigApp:
    """Provide only the connection configuration needed by the manager."""

    def __init__(self, connections: dict[str, dict[str, object]]) -> None:
        """Store the configured named database connections.

        Parameters
        ----------
        connections : dict[str, dict[str, object]]
            Connection settings keyed by connection name.
        """
        self._connections = connections

    def config(self, name: str) -> dict[str, object]:
        """Return the configured named SQLite databases.

        Parameters
        ----------
        name : str
            Configuration section requested by the connection manager.

        Returns
        -------
        dict[str, object]
            Default connection name and named connection settings.

        Raises
        ------
        ValueError
            If a configuration section other than ``database`` is requested.
        """
        if name != "database":
            error_msg = f"Unexpected configuration key: {name}"
            raise ValueError(error_msg)
        return {"default": "primary", "connections": self._connections}

class _Transaction:
    """Keep a fake connection's statements inside one apparent transaction."""

    async def __aenter__(self) -> None:
        """Enter the fake transaction.

        Returns
        -------
        None
            Begin the simulated transaction context.
        """

    async def __aexit__(self, *_args: object) -> None:
        """Leave the fake transaction.

        Parameters
        ----------
        _args : object
            Exception details supplied by the asynchronous context manager.

        Returns
        -------
        None
            Finish the simulated transaction context.
        """

class _UnresolvedManager:
    """Reject connection resolution before a wipe is confirmed."""

    __slots__ = ()

    def getDefaultName(self) -> str:
        """Return the selected default connection.

        Returns
        -------
        str
            Default connection name.
        """
        return "primary"

    def configFor(self, _name: str) -> None:
        """Reject a configuration lookup before confirmation.

        Parameters
        ----------
        _name : str
            Connection name that should not be resolved.

        Raises
        ------
        AssertionError
            Always, because no connection should be opened.
        """
        message = "Database connection resolved before confirmation."
        raise AssertionError(message)

class TestDbWipeCommand(TestCase):
    """Exercise the command against isolated SQLite files."""

    async def asyncSetUp(self) -> None:
        """Create two named databases with foreign keys enabled.

        Returns
        -------
        None
            Prepare isolated SQLite files for the command tests.
        """
        self._temporary = TemporaryDirectory()
        root = Path(self._temporary.name)
        self.manager = ConnectionManager(
            _ConfigApp({
                name: {
                    "driver": "sqlite",
                    "database": str(root / f"{name}.sqlite"),
                    "prefix": "",
                    "foreign_key_constraints": True,
                }
                for name in ("primary", "archive")
            }),
        )

    async def asyncTearDown(self) -> None:
        """Dispose database engines before removing temporary files.

        Returns
        -------
        None
            Close connections and remove the temporary database directory.
        """
        await self.manager.disconnect()
        self._temporary.cleanup()

    async def testWipeRemovesCircularForeignKeysViewsAndHistories(self) -> None:
        """Clear objects in one connection while preserving another.

        Returns
        -------
        None
            Verify tables, views, and histories are removed only from the target.
        """
        primary = self.manager.connection("primary")
        archive = self.manager.connection("archive")
        await primary.statement(
            'CREATE TABLE "a" (id INTEGER PRIMARY KEY, b_id INTEGER '
            'REFERENCES "b"(id))',
        )
        await primary.statement(
            'CREATE TABLE "b" (id INTEGER PRIMARY KEY, a_id INTEGER '
            'REFERENCES "a"(id))',
        )
        await primary.statement('INSERT INTO "a" VALUES (1, NULL)')
        await primary.statement('INSERT INTO "b" VALUES (1, 1)')
        await primary.statement('UPDATE "a" SET b_id = 1 WHERE id = 1')
        await primary.statement('CREATE VIEW "a_view" AS SELECT id FROM "a"')
        await primary.statement('CREATE TABLE "migrations" (id INTEGER)')
        await primary.statement('CREATE TABLE "seeders" (id INTEGER)')
        await primary.statement('CREATE TABLE "odd.name" (id INTEGER)')
        await primary.statement('CREATE TABLE "odd""quote" (id INTEGER)')
        await primary.statement('CREATE TABLE "sqliteXvisible" (id INTEGER)')
        await archive.statement('CREATE TABLE "keep_me" (id INTEGER)')

        command = DbWipeCommand()
        command.setArguments({"database": "primary", "force": True})
        with patch.object(command, "success") as success:
            status = await command.handle(self.manager)

        self.assertEqual(status, 0)
        self.assertIn("7 table(s), 1 view(s)", success.call_args.args[0])
        primary_inspector = DatabaseInspector(self.manager, "primary")
        self.assertEqual(await primary_inspector.listTables(), [])
        self.assertEqual(await primary_inspector.listViews(), [])
        self.assertEqual(
            await DatabaseInspector(self.manager, "archive").listTables(),
            ["keep_me"],
        )

    async def testWithoutForceNoninteractiveSessionCannotWipe(self) -> None:
        """Require explicit ``--force`` in automation without a terminal.

        Returns
        -------
        None
            Verify a noninteractive wipe is rejected and preserves database data.
        """
        primary = self.manager.connection("primary")
        await primary.statement('CREATE TABLE "keep_me" (id INTEGER)')
        command = DbWipeCommand()
        command.setArguments({"database": "primary"})
        with (
            patch("orionis.console.commands.db.wipe.sys.stdin") as stdin,
            patch.object(command, "error") as report_error,
            patch.object(command, "confirm") as confirm,
        ):
            stdin.isatty.return_value = False
            status = await command.handle(self.manager)

        self.assertEqual(status, 1)
        confirm.assert_not_called()
        self.assertIn("--force", report_error.call_args.args[0])
        self.assertEqual(
            await DatabaseInspector(self.manager, "primary").listTables(),
            ["keep_me"],
        )

    async def testUnconfirmedWipeDoesNotResolveConnection(self) -> None:
        """Leave connection setup until after explicit confirmation.

        Returns
        -------
        None
            Verify an unconfirmed wipe exits before resolving a connection.
        """
        command = DbWipeCommand()
        command.setArguments({})
        with (
            patch("orionis.console.commands.db.wipe.sys.stdin") as stdin,
            patch.object(command, "error"),
        ):
            stdin.isatty.return_value = False
            self.assertEqual(await command.handle(_UnresolvedManager()), 1)

    async def testDeclinedConfirmationPreservesObjects(self) -> None:
        """Preserve database objects after an explicit refusal.

        Returns
        -------
        None
            Verify the command asks about the selected database and changes nothing.
        """
        primary = self.manager.connection("primary")
        await primary.statement('CREATE TABLE "keep_me" (id INTEGER)')
        command = DbWipeCommand()
        command.setArguments({"database": "primary"})
        with (
            patch("orionis.console.commands.db.wipe.sys.stdin") as stdin,
            patch.object(command, "confirm", return_value=False) as confirm,
            patch.object(command, "info"),
        ):
            stdin.isatty.return_value = True
            status = await command.handle(self.manager)

        self.assertEqual(status, 0)
        self.assertIn("primary", confirm.call_args.args[0])
        self.assertEqual(
            await DatabaseInspector(self.manager, "primary").listTables(),
            ["keep_me"],
        )

    def testWipeOptionsParseNamedConnectionAndForce(self) -> None:
        """Expose Laravel-style options through the console parser.

        Returns
        -------
        None
            Verify the parser accepts the connection name and force flag.
        """
        parser = argparse.ArgumentParser()
        for argument in DbWipeCommand.arguments:
            argument.addToParser(parser)
        parsed = parser.parse_args(["-d", "archive", "--force"])
        self.assertEqual(parsed.database, "archive")
        self.assertTrue(parsed.force)

class TestDatabaseWiperDialects(TestCase):
    """Check generated DDL where server database drivers are unavailable."""

    def testDependencyOrderHandlesBranchesAndRejectsCycles(self) -> None:
        """Drop dependents first and reject cycles before issuing DDL.

        Returns
        -------
        None
            Verify dependency ordering and cycle detection.
        """
        dependencies = {
            "root": set(),
            "left": {"root"},
            "right": {"root"},
            "leaf": {"left", "right"},
        }
        self.assertEqual(
            DatabaseWiper._dependencyOrder(dependencies, "cycle"),
            ["leaf", "left", "right", "root"],
        )
        with self.assertRaisesRegex(RuntimeError, "cycle"):
            DatabaseWiper._dependencyOrder(
                {"left": {"right"}, "right": {"left"}},
                "cycle",
            )

    @staticmethod
    def _inspector(  # noqa: PLR0913
        driver: str,
        *,
        tables: list[str] | None = None,
        views: list[str] | None = None,
        materialized_views: list[str] | None = None,
        types: list[str] | None = None,
        domains: list[str] | None = None,
        metadata: list[dict[str, str]] | None = None,
    ) -> SimpleNamespace:
        """Build a fake inspector recording statements for a dialect.

        Parameters
        ----------
        driver : str
            Database dialect to expose to the wiper.
        tables : list[str] or None, optional
            Table names returned by the inspector.
        views : list[str] or None, optional
            View names returned by the inspector.
        materialized_views : list[str] or None, optional
            Materialized-view names returned by the inspector.
        types : list[str] or None, optional
            User-defined type names returned by the inspector.
        domains : list[str] or None, optional
            Domain names returned by the inspector.
        metadata : list[dict[str, str]] or None, optional
            Catalog rows returned by connection queries.

        Returns
        -------
        SimpleNamespace
            Inspector double with recording connection operations.
        """
        connection = Mock()
        connection.transaction.return_value = _Transaction()
        connection.statement = AsyncMock(return_value=True)
        connection.select = AsyncMock(return_value=metadata or [])
        quote = DatabaseInspector.quoteIdentifier
        return SimpleNamespace(
            driver=driver,
            connection=connection,
            quoteIdentifier=lambda name, **kwargs: quote(
                SimpleNamespace(driver=driver), name, **kwargs,
            ),
            listTables=AsyncMock(return_value=tables or []),
            listViews=AsyncMock(return_value=views or []),
            listMaterializedViews=AsyncMock(return_value=materialized_views or []),
            listTypes=AsyncMock(return_value=types or []),
            listDomains=AsyncMock(return_value=domains or []),
        )

    async def testPostgresDropsMaterializedViewsTablesAndTypes(self) -> None:
        """Use ``CASCADE`` and quote schema-qualified PostgreSQL names.

        Returns
        -------
        None
            Verify PostgreSQL objects are dropped in dependency-safe order.
        """
        inspector = self._inspector(
            "pgsql",
            tables=["app.users"],
            views=["app.active_users"],
            materialized_views=["app.user_counts"],
            types=["app.user_state"],
            domains=["app.email_address"],
        )
        result = await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual((result.tables, result.views, result.types), (1, 2, 2))
        self.assertEqual(sql, [
            'DROP MATERIALIZED VIEW IF EXISTS "app"."user_counts" CASCADE',
            'DROP VIEW IF EXISTS "app"."active_users" CASCADE',
            'DROP TABLE IF EXISTS "app"."users" CASCADE',
            'DROP DOMAIN IF EXISTS "app"."email_address" CASCADE',
            'DROP TYPE IF EXISTS "app"."user_state" CASCADE',
        ])

    async def testMySqlRestoresForeignKeyChecksAfterFailure(self) -> None:
        """Restore session checks even when a drop statement fails.

        Returns
        -------
        None
            Verify foreign-key checks are re-enabled after a failed drop.
        """
        inspector = self._inspector(
            "mysql", tables=["orders"], metadata=[{"enabled": 1}],
        )

        async def statement(sql: str) -> bool:
            """Raise for table drops and accept foreign-key setting changes.

            Parameters
            ----------
            sql : str
                Statement issued by the database wiper.

            Returns
            -------
            bool
                Whether a non-drop statement succeeded.

            Raises
            ------
            RuntimeError
                If the statement attempts to drop a table.
            """
            if sql.startswith("DROP TABLE"):
                error_msg = "simulated drop failure"
                raise RuntimeError(error_msg)
            return True

        inspector.connection.statement.side_effect = statement
        with self.assertRaisesRegex(RuntimeError, "simulated drop failure"):
            await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual(sql, [
            "SET FOREIGN_KEY_CHECKS = 0",
            "DROP TABLE IF EXISTS `orders`",
            "SET FOREIGN_KEY_CHECKS = 1",
        ])

    async def testMySqlPreservesInitiallyDisabledForeignKeyChecks(self) -> None:
        """Preserve the session's initially disabled foreign-key setting.

        Returns
        -------
        None
            Verify the wiper restores the setting observed before execution.
        """
        inspector = self._inspector(
            "mysql", tables=["orders"], metadata=[{"enabled": 0}],
        )
        await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual(sql[0], "SET FOREIGN_KEY_CHECKS = 0")
        self.assertEqual(sql[-1], "SET FOREIGN_KEY_CHECKS = 0")

    async def testPostgresCatalogSeparatesDomainsAndBaseTypes(self) -> None:
        """Select domains separately from ordinary user-defined types.

        Returns
        -------
        None
            Verify PostgreSQL catalog queries distinguish domains and base types.
        """
        manager = Mock()
        manager.configFor.return_value = {"driver": "pgsql"}
        connection = Mock()
        connection.select = AsyncMock(side_effect=[
            [{"name": "app.custom_base"}],
            [{"name": "app.email_address"}],
        ])
        manager.connection.return_value = connection
        inspector = DatabaseInspector(manager, "reports")

        self.assertEqual(await inspector.listTypes(), ["app.custom_base"])
        self.assertEqual(await inspector.listDomains(), ["app.email_address"])
        type_query = connection.select.await_args_list[0].args[0]
        domain_query = connection.select.await_args_list[1].args[0]
        self.assertIn("t.typtype = 'b'", type_query)
        self.assertIn("t.typcategory <> 'A'", type_query)
        self.assertIn("d.deptype IN ('e', 'i')", type_query)
        self.assertNotIn("'d'", type_query)
        self.assertIn("t.typtype = 'd'", domain_query)

    async def testSqlServerDropsViewDependenciesAndForeignKeysFirst(self) -> None:
        """Prepare temporal tables and constraints before removing tables.

        Returns
        -------
        None
            Verify dependent views and constraints are removed before tables.
        """
        inspector = self._inspector(
            "sqlserver",
            tables=["dbo.parent", "dbo.child"],
            views=["dbo.base_view", "dbo.dependent_view"],
            types=["dbo.custom_type"],
        )

        async def select(sql: str) -> list[dict[str, str]]:
            """Return catalog rows for the requested SQL Server query.

            Parameters
            ----------
            sql : str
                Catalog query issued by the database wiper.

            Returns
            -------
            list[dict[str, str]]
                Matching table, view, or type dependency rows.
            """
            if "sys.table_types" in sql:
                return []
            if "sys.sql_expression_dependencies" in sql:
                return [{
                    "schema_name": "dbo",
                    "view_name": "dependent_view",
                    "referenced_schema": "dbo",
                    "referenced_view": "base_view",
                }]
            if "temporal_type" in sql:
                return [{"schema_name": "dbo", "table_name": "parent"}]
            return [{
                "schema_name": "dbo",
                "table_name": "child",
                "constraint_name": "fk.child",
            }]

        inspector.connection.select.side_effect = select
        await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual(sql[:4], [
            "DROP VIEW IF EXISTS [dbo].[dependent_view]",
            "DROP VIEW IF EXISTS [dbo].[base_view]",
            "ALTER TABLE [dbo].[parent] SET (SYSTEM_VERSIONING = OFF)",
            "ALTER TABLE [dbo].[child] DROP CONSTRAINT [fk.child]",
        ])
        self.assertIn("DROP TABLE IF EXISTS [dbo].[parent]", sql)
        self.assertEqual(sql[-1], "DROP TYPE IF EXISTS [dbo].[custom_type]")

    async def testSqlServerOrdersTableTypesBeforeColumnTypes(self) -> None:
        """Drop a table type before an alias used by one of its columns.

        Returns
        -------
        None
            Verify dependent SQL Server types are dropped before their aliases.
        """
        inspector = self._inspector(
            "sqlserver", types=["dbo.alias_type", "dbo.row_type"],
        )

        async def select(sql: str) -> list[dict[str, str]]:
            """Return dependencies between SQL Server table types.

            Parameters
            ----------
            sql : str
                Catalog query issued by the database wiper.

            Returns
            -------
            list[dict[str, str]]
                Type dependency rows, or an empty list for other queries.
            """
            if "sys.table_types" in sql:
                return [{
                    "dependent_schema": "dbo", "dependent_type": "row_type",
                    "referenced_schema": "dbo", "referenced_type": "alias_type",
                }]
            return []

        inspector.connection.select.side_effect = select
        await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual(sql, [
            "DROP TYPE IF EXISTS [dbo].[row_type]",
            "DROP TYPE IF EXISTS [dbo].[alias_type]",
        ])

    async def testSqlServerRejectsAmbiguousQualifiedNameBeforeDdl(self) -> None:
        """Reject dotted object names that could identify another database.

        Returns
        -------
        None
            Verify ambiguous names fail before any DDL is issued.
        """
        inspector = self._inspector("sqlserver", tables=["dbo.odd.name"])
        with self.assertRaisesRegex(ValueError, "contains a period"):
            await DatabaseWiper(inspector).wipe()
        inspector.connection.statement.assert_not_awaited()

    async def testOracleDropsTypesAfterTables(self) -> None:
        """Use Oracle's constraint clause and avoid unsafe ``TYPE FORCE``.

        Returns
        -------
        None
            Verify views, tables, and types are dropped with Oracle syntax.
        """
        inspector = self._inspector(
            "oracle", tables=["ORDERS"], views=["ORDER_VIEW"], types=["ORDER_KIND"],
        )
        await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual(sql, [
            'DROP VIEW "ORDER_VIEW"',
            'DROP TABLE "ORDERS" CASCADE CONSTRAINTS PURGE',
            'DROP TYPE "ORDER_KIND"',
        ])

    async def testOracleDropsDependentTypesFirst(self) -> None:
        """Order dependent Oracle types before their referenced types.

        Returns
        -------
        None
            Verify referenced types remain until dependent types are dropped.
        """
        inspector = self._inspector(
            "oracle", types=["PARENT_KIND", "CHILD_KIND"],
            metadata=[{
                "owner": "APP", "name": "CHILD_KIND", "object_type": "TYPE",
                "referenced_owner": "APP", "referenced_name": "PARENT_KIND",
            }],
        )
        await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual(sql, [
            'DROP TYPE "CHILD_KIND"',
            'DROP TYPE "PARENT_KIND"',
        ])

    async def testOracleDropsMaterializedViewAndItsPrebuiltTable(self) -> None:
        """Discover a prebuilt table exposed after dropping its materialized view.

        Returns
        -------
        None
            Verify the newly exposed table is also removed.
        """
        inspector = self._inspector(
            "oracle", materialized_views=["ORDER_CACHE"],
        )
        inspector.listTables.side_effect = [[], ["ORDER_CACHE"]]
        result = await DatabaseWiper(inspector).wipe()
        sql = [call.args[0] for call in inspector.connection.statement.await_args_list]
        self.assertEqual(sql, [
            'DROP MATERIALIZED VIEW "ORDER_CACHE"',
            'DROP TABLE "ORDER_CACHE" CASCADE CONSTRAINTS PURGE',
        ])
        self.assertEqual((result.tables, result.views), (1, 1))

    async def testOracleRejectsOutOfScopeTypeDependentsBeforeDropping(self) -> None:
        """Reject cross-schema type dependents before issuing irreversible DDL.

        Returns
        -------
        None
            Verify out-of-scope dependencies prevent all drop statements.
        """
        inspector = self._inspector(
            "oracle", tables=["OWN_TABLE"], types=["OWN_KIND"],
            metadata=[{
                "owner": "OTHER", "name": "FOREIGN_TABLE", "object_type": "TABLE",
                "referenced_owner": "APP", "referenced_name": "OWN_KIND",
            }],
        )
        with self.assertRaisesRegex(RuntimeError, "outside the wipe scope"):
            await DatabaseWiper(inspector).wipe()
        inspector.connection.statement.assert_not_awaited()
