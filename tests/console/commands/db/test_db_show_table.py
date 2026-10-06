import argparse
from unittest.mock import AsyncMock, Mock, patch
from orionis.console.commands.db._inspection import DatabaseInspector
from orionis.console.commands.db.show import DbShowCommand
from orionis.console.commands.db.table import DbTableCommand
from orionis.database.connection import Connection
from orionis.database.exceptions import QueryException
from orionis.test import TestCase

class _Manager:
    """Provide two isolated in-memory connections to the commands."""

    def __init__(self) -> None:
        """Create isolated in-memory connections for each configured name.

        Returns
        -------
        None
            Store the named connections.
        """
        self.connections = {
            name: Connection(name, {"driver": "sqlite", "database": ":memory:"})
            for name in ("default", "reports")
        }

    def getDefaultName(self) -> str:
        """Return the default connection name.

        Returns
        -------
        str
            Default connection name.
        """
        return "default"

    def configFor(self, _name: str) -> dict[str, str]:
        """Return the in-memory SQLite configuration.

        Parameters
        ----------
        _name : str
            Name of the requested connection.

        Returns
        -------
        dict[str, str]
            SQLite connection settings.
        """
        return {"driver": "sqlite", "database": ":memory:"}

    def connection(self, name: str) -> Connection:
        """Resolve a configured connection by name.

        Parameters
        ----------
        name : str
            Name of the connection to resolve.

        Returns
        -------
        Connection
            Requested SQLite connection.
        """
        return self.connections[name]

class _RecordingConnection:
    """Record catalog reads while delegating to a real SQLite connection."""

    __slots__ = ("delegate", "queries")

    def __init__(self, delegate: Connection) -> None:
        """Keep the connection used for SQL execution.

        Parameters
        ----------
        delegate : Connection
            Real SQLite connection used by the test.
        """
        self.delegate = delegate
        self.queries: list[str] = []

    async def select(
        self,
        query: str,
        bindings: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        """Record a query and return its rows.

        Parameters
        ----------
        query : str
            SQL statement to execute.
        bindings : dict[str, object] | None, optional
            Bound SQL parameters.

        Returns
        -------
        list[dict[str, object]]
            Rows returned by the SQLite connection.
        """
        self.queries.append(query)
        return await self.delegate.select(query, bindings)

    async def disconnect(self) -> None:
        """Close the underlying SQLite connection.

        Returns
        -------
        None
            The connection is closed.
        """
        await self.delegate.disconnect()

class _CatalogConnection:
    """Return a fixed table name from a catalog query."""

    __slots__ = ("queries", "rows")

    def __init__(self, name: str) -> None:
        """Set the catalog name returned to the inspector.

        Parameters
        ----------
        name : str
            Table name present in the fake catalog.
        """
        self.rows = [{"name": name}]
        self.queries: list[str] = []

    async def select(
        self,
        query: str,
        _bindings: dict[str, object] | None = None,
    ) -> list[dict[str, str]]:
        """Record the query and return the configured catalog row.

        Parameters
        ----------
        query : str
            Catalog query to record.
        _bindings : dict[str, object] | None, optional
            Bound SQL parameters unused by this fixed-result double.

        Returns
        -------
        list[dict[str, str]]
            One table name row.
        """
        self.queries.append(query)
        return self.rows

class _FailingMetadataConnection:
    """Raise a configured failure when metadata is queried."""

    __slots__ = ("failure",)

    def __init__(self, failure: Exception) -> None:
        """Store the failure returned by catalog access.

        Parameters
        ----------
        failure : Exception
            Exception to raise from a metadata query.
        """
        self.failure = failure

    async def select(
        self,
        _query: str,
        _bindings: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        """Raise the configured catalog error.

        Parameters
        ----------
        _query : str
            SQL statement that would be executed.
        _bindings : dict[str, object] | None, optional
            Bound SQL parameters.

        Returns
        -------
        list[dict[str, object]]
            This method never returns rows.

        Raises
        ------
        Exception
            The configured failure.
        """
        raise self.failure

class TestDbShowTableCommands(TestCase):
    """Validate real catalog inspection and named connection selection."""

    async def asyncSetUp(self) -> None:
        """Create a small schema on the named reporting connection.

        Returns
        -------
        None
            Prepare tables, indexes, a view, and representative rows.
        """
        self.manager = _Manager()
        connection = self.manager.connection("reports")
        await connection.statement("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        await connection.statement(
            "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER "
            "NOT NULL REFERENCES parent(id), label TEXT DEFAULT 'new')",
        )
        await connection.statement("CREATE INDEX child_label_idx ON child(label)")
        await connection.statement("CREATE VIEW child_view AS SELECT id FROM child")
        await connection.statement("INSERT INTO parent(id) VALUES (1)")
        await connection.statement(
            "INSERT INTO child(id, parent_id, label) VALUES (5, 1, 'saved')",
        )

    async def asyncTearDown(self) -> None:
        """Dispose the database engines after each test.

        Returns
        -------
        None
            Close both in-memory SQLite connections.
        """
        for connection in self.manager.connections.values():
            await connection.disconnect()

    def testParsersAcceptLaravelStyleOptions(self) -> None:
        """Accept the documented connection and inspection flags.

        Returns
        -------
        None
            Verify database, count, view, and table arguments are parsed.
        """
        show_parser = argparse.ArgumentParser()
        for argument in DbShowCommand.arguments:
            argument.addToParser(show_parser)
        options = show_parser.parse_args(
            ["--database", "reports", "--counts", "--views"],
        )
        self.assertEqual(options.database, "reports")
        self.assertTrue(options.counts)
        self.assertTrue(options.views)

        table_parser = argparse.ArgumentParser()
        for argument in DbTableCommand.arguments:
            argument.addToParser(table_parser)
        options = table_parser.parse_args(["child", "-d", "reports"])
        self.assertEqual(options.table, "child")
        self.assertEqual(options.database, "reports")

    async def testSQLiteCatalogIncludesColumnsIndexesAndForeignKeys(self) -> None:
        """Read real SQLite schema details and connection summary.

        Returns
        -------
        None
            Verify catalog objects, columns, indexes, keys, and database size.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        self.assertEqual(await inspector.listTables(), ["child", "parent"])
        self.assertEqual(await inspector.listViews(), ["child_view"])
        self.assertEqual(await inspector.listTypes(), [])
        self.assertEqual(await inspector.listMaterializedViews(), [])
        self.assertEqual(inspector.quoteIdentifier("a.b"), '"a.b"')
        self.assertIsNone(await inspector.connectionCount())
        self.assertGreater(await inspector.databaseSize(), 0)

        details = await inspector.tableDetails("child")
        self.assertEqual(details["rows"], 1)
        self.assertEqual(
            [(column["name"], column["primary"]) for column in details["columns"]],
            [("id", True), ("parent_id", False), ("label", False)],
        )
        self.assertFalse(details["columns"][1]["nullable"])
        self.assertEqual(details["columns"][2]["default"], "'new'")
        self.assertEqual(details["indexes"][0]["name"], "child_label_idx")
        self.assertEqual(details["foreign_keys"][0]["references"], "parent.id")

    async def testMetadataFallbackHandlesWrappedDatabaseErrors(self) -> None:
        """Return unknown metadata for query failures and expose coding errors.

        Returns
        -------
        None
            Verify database errors are handled while programming errors escape.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.connection = _FailingMetadataConnection(
            QueryException("metadata unavailable"),
        )

        self.assertIsNone(await inspector.tableSize("child"))
        self.assertEqual(await inspector.tableSizes(["child"]), {})
        inspector.driver = "pgsql"
        self.assertIsNone(await inspector.connectionCount())

        inspector.driver = "sqlite"
        inspector.connection = _FailingMetadataConnection(
            TypeError("unexpected metadata result"),
        )
        with self.assertRaisesRegex(TypeError, "unexpected metadata result"):
            await inspector.tableSizes(["child"])

    async def testOverviewBatchesTableSizesAndCountsViews(self) -> None:
        """Read sizes and view counts with a fixed number of catalog queries.

        Returns
        -------
        None
            Verify table sizes and view counts use batched catalog reads.
        """
        connection = self.manager.connection("reports")
        for number in range(30):
            await connection.statement(f"CREATE TABLE extra_{number} (id INTEGER)")
        await connection.statement("CREATE VIEW extra_view AS SELECT id FROM parent")
        recording = _RecordingConnection(connection)
        self.manager.connections["reports"] = recording
        inspector = DatabaseInspector(self.manager, "reports")

        tables = await inspector.listTables()
        sizes = await inspector.tableSizes(tables)
        view_counts = await inspector.viewCounts()

        self.assertEqual(len(tables), 32)
        self.assertEqual(len(sizes), 32)
        self.assertEqual(view_counts, (2, 0))
        self.assertEqual(len(recording.queries), 3)
        self.assertIn("GROUP BY name", recording.queries[1])
        self.assertIn("COUNT(*)", recording.queries[2])
        self.assertEqual(sizes["child"], await inspector.tableSize("child"))
        self.assertEqual(sizes["parent"], await inspector.tableSize("parent"))

    async def testTableLookupFiltersCatalogBeforeLoadingRows(self) -> None:
        """Resolve one table without returning unrelated catalog names.

        Returns
        -------
        None
            Verify the catalog query filters by the requested table name.
        """
        connection = self.manager.connection("reports")
        for number in range(30):
            await connection.statement(f"CREATE TABLE extra_{number} (id INTEGER)")
        recording = _RecordingConnection(connection)
        self.manager.connections["reports"] = recording
        inspector = DatabaseInspector(self.manager, "reports")

        details = await inspector.tableDetails("child")

        self.assertEqual(details["name"], "child")
        self.assertIn("AND name = :name", recording.queries[0])

    async def testSQLiteIndexesUseOneCatalogQuery(self) -> None:
        """Read every index and its ordered columns in one query.

        Returns
        -------
        None
            Verify index columns, uniqueness, and query count.
        """
        connection = self.manager.connection("reports")
        await connection.statement(
            "CREATE UNIQUE INDEX child_parent_label_idx "
            "ON child(parent_id, label)",
        )
        recording = _RecordingConnection(connection)
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.connection = recording

        _, indexes, _ = await inspector._sqliteDetails("child")

        by_name = {index["name"]: index for index in indexes}
        self.assertEqual(by_name["child_label_idx"]["columns"], "label")
        self.assertEqual(
            by_name["child_parent_label_idx"]["columns"],
            "parent_id, label",
        )
        self.assertTrue(by_name["child_parent_label_idx"]["unique"])
        self.assertEqual(len(recording.queries), 3)

    async def testQualifiedCatalogNameWithPeriodIsRejected(self) -> None:
        """Reject names that could become a three-part SQL reference.

        Returns
        -------
        None
            Verify ambiguous qualified names fail before additional queries.
        """
        for driver in ("pgsql", "redshift", "sqlserver"):
            with self.subTest(driver=driver):
                inspector = DatabaseInspector(self.manager, "reports")
                catalog = _CatalogConnection("dbo.odd.name")
                inspector.driver = driver
                inspector.connection = catalog
                with self.assertRaisesRegex(ValueError, "contains a period"):
                    await inspector.tableDetails("dbo.odd.name")
                self.assertEqual(len(catalog.queries), 1)

    async def testQuotedAndReservedLikeSQLiteNames(self) -> None:
        """Keep literal dots and exclude only the reserved sqlite_ prefix.

        Returns
        -------
        None
            Verify quoted names remain literal and reserved names are filtered.
        """
        connection = self.manager.connection("reports")
        await connection.statement('CREATE TABLE "a.b" (id INTEGER)')
        await connection.statement("CREATE TABLE sqliteX_user (id INTEGER)")
        inspector = DatabaseInspector(self.manager, "reports")
        self.assertIn("a.b", await inspector.listTables())
        self.assertIn("sqliteX_user", await inspector.listTables())
        self.assertEqual((await inspector.tableDetails("a.b"))["rows"], 0)

    def testQualifiedNamesRespectDialectRules(self) -> None:
        """Quote schema components and resolve unique SQL Server short names.

        Returns
        -------
        None
            Verify identifier quoting and unique short-name resolution.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "pgsql"
        self.assertEqual(
            inspector.quoteIdentifier("Public.Users"),
            '"Public"."Users"',
        )
        inspector.driver = "sqlserver"
        self.assertEqual(inspector.quoteIdentifier("dbo.Users"), "[dbo].[Users]")
        self.assertEqual(
            inspector.quoteIdentifier("a.b", qualified=False),
            "[a.b]",
        )
        self.assertEqual(
            inspector._resolveTableName("users", ["dbo.Users"]),
            "dbo.Users",
        )

    async def testPostgreSQLMetadataMapsPrimaryAndForeignKeys(self) -> None:
        """Display catalog key columns, referenced table, and delete rule.

        Returns
        -------
        None
            Verify PostgreSQL catalog rows map to the expected key metadata.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "pgsql"
        catalog = Mock()
        catalog.select = AsyncMock(side_effect=[
            [{
                "name": "parent_id",
                "type": "integer",
                "nullable": "NO",
                "default_value": None,
                "primary_key": 0,
            }],
            [{
                "name": "child_parent_id_idx",
                "definition": "parent_id",
                "non_unique": 1,
                "primary_key": False,
            }],
            [{
                "name": "child_parent_id_fkey",
                "column_name": "parent_id",
                "ref_table": "public.parent",
                "ref_column": "id",
                "on_delete": "CASCADE",
            }],
        ])
        inspector.connection = catalog

        columns, indexes, keys = await inspector._serverDetails("public.child")
        self.assertFalse(columns[0]["nullable"])
        self.assertEqual(indexes[0]["columns"], "parent_id")
        self.assertFalse(indexes[0]["unique"])
        self.assertEqual(keys[0]["column"], "parent_id")
        self.assertEqual(keys[0]["references"], "public.parent.id")
        self.assertEqual(keys[0]["on_delete"], "CASCADE")
        fk_query = catalog.select.await_args_list[2].args[0]
        self.assertIn("unnest(c.conkey, c.confkey)", fk_query)

    async def testOracleForeignKeyUsesReferencedTable(self) -> None:
        """Resolve the Oracle foreign-key target and retain identifier case.

        Returns
        -------
        None
            Verify the parent constraint supplies the referenced table details.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "oracle"
        catalog = Mock()
        catalog.select = AsyncMock(side_effect=[
            [{
                "name": "ParentId",
                "type": "NUMBER",
                "nullable": "N",
                "default_value": None,
                "primary_key": 0,
            }],
            [{
                "name": "ChildParentIdx",
                "definition": "ParentId",
                "non_unique": 1,
                "primary_key": 1,
            }],
            [{
                "name": "ChildParentFk",
                "column_name": "ParentId",
                "ref_table": "APP.Parent",
                "ref_column": "Id",
                "on_delete": "CASCADE",
            }],
        ])
        inspector.connection = catalog

        _, indexes, keys = await inspector._serverDetails("Child")
        self.assertTrue(indexes[0]["primary"])
        self.assertEqual(keys[0]["references"], "APP.Parent.Id")
        self.assertEqual(keys[0]["on_delete"], "CASCADE")
        self.assertEqual(catalog.select.await_args_list[0].args[1], {"table": "Child"})
        fk_query = catalog.select.await_args_list[2].args[0]
        self.assertIn("all_constraints parent", fk_query)
        self.assertIn("all_cons_columns pc", fk_query)
        index_query = catalog.select.await_args_list[1].args[0]
        self.assertIn("pk.index_name = i.index_name", index_query)

    async def testOracleListsMaterializedViewsSeparately(self) -> None:
        """Keep materialized-view containers out of ordinary table names.

        Returns
        -------
        None
            Verify Oracle lists materialized views separately from tables.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "oracle"
        catalog = Mock()
        catalog.select = AsyncMock(side_effect=[
            [{"name": "PARENT"}],
            [{"name": "CHILD_MV"}],
        ])
        inspector.connection = catalog
        self.assertEqual(await inspector.listTables(), ["PARENT"])
        self.assertEqual(await inspector.listMaterializedViews(), ["CHILD_MV"])
        tables_query = catalog.select.await_args_list[0].args[0]
        self.assertIn("user_mviews", tables_query)
        self.assertIn("container_name", tables_query)

    async def testSqlServerTableSizeCountsRowAndLargeObjects(self) -> None:
        """Use the correct allocation container for each page type.

        Returns
        -------
        None
            Verify row and large-object page allocations are included.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "sqlserver"
        catalog = Mock()
        catalog.select = AsyncMock(return_value=[{"bytes": 16384}])
        inspector.connection = catalog
        self.assertEqual(await inspector.tableSize("dbo.Child"), 16384)
        sql = catalog.select.await_args.args[0]
        self.assertIn("a.container_id = p.hobt_id", sql)
        self.assertIn("a.container_id = p.partition_id", sql)
        self.assertEqual(catalog.select.await_args.args[1], {"name": "[dbo].[Child]"})

    async def testShowUsesSelectedConnectionAndOnlyCountsWhenRequested(self) -> None:
        """Render named connection data and make row counting opt-in.

        Returns
        -------
        None
            Verify selected-connection output and optional row counts.
        """
        command = DbShowCommand()
        command.setArguments({"database": "reports", "views": True, "counts": True})
        rendered: list[tuple[list[str], list[list[str]]]] = []
        with (
            patch.object(
                command,
                "table",
                side_effect=lambda headers, rows: rendered.append((headers, rows)),
            ),
            patch.object(command, "newLine"),
        ):
            await command.handle(self.manager)

        overview = dict(rendered[0][1])
        self.assertEqual(overview["Connection"], "reports")
        self.assertEqual(overview["Tables"], "2")
        self.assertEqual(overview["Views"], "1")
        self.assertEqual(overview["Open connections"], "N/A")
        self.assertEqual(rendered[1][0], ["Table", "Size", "Rows"])
        self.assertEqual(
            {row[0]: row[2] for row in rendered[1][1]},
            {"child": "1", "parent": "1"},
        )
        self.assertEqual(rendered[2][1], [["child_view", "View"]])

        command = DbShowCommand()
        command.setArguments({"database": "reports"})
        with (
            patch.object(command, "table") as table,
            patch.object(command, "newLine"),
            patch.object(
                DatabaseInspector,
                "rowCount",
                side_effect=AssertionError("COUNT called"),
            ),
        ):
            await command.handle(self.manager)
        self.assertEqual(table.call_args_list[1].args[0], ["Table", "Size"])

    async def testTableCommandReportsUnknownTableAndPrintsDetails(self) -> None:
        """Render table details and report missing tables cleanly.

        Returns
        -------
        None
            Verify details render and unknown table names return an error.
        """
        command = DbTableCommand()
        command.setArguments({"database": "reports", "table": "child"})
        with (
            patch.object(command, "table") as table,
            patch.object(command, "newLine"),
        ):
            self.assertEqual(await command.handle(self.manager), 0)
        self.assertEqual(table.call_args_list[1].args[0][0], "Column")
        self.assertEqual(table.call_args_list[2].args[0][0], "Index")
        self.assertEqual(table.call_args_list[3].args[0][0], "Foreign key")

        missing = DbTableCommand()
        missing.setArguments({"database": "reports", "table": "missing"})
        with patch.object(missing, "error") as error:
            self.assertEqual(await missing.handle(self.manager), 1)
        self.assertIn("does not exist", error.call_args.args[0])

    async def testRedshiftCatalogSeparatesNativeObjectsAndBatchesCounts(self) -> None:
        """Use AWS catalogs without partition columns or Oracle metadata fallback.

        Returns
        -------
        None
            Tables, ordinary views and materialized views stay separate.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "redshift"
        catalog = Mock()
        catalog.select = AsyncMock(side_effect=[
            [{"name": "analytics.events"}], [{"name": "analytics.active"}],
            [{"name": "analytics.summary"}],
            [{"object_count": 1}], [{"object_count": 2}], [{"count": 3}],
        ])
        inspector.connection = catalog
        self.assertEqual(await inspector.listTables(), ["analytics.events"])
        self.assertEqual(await inspector.listViews(), ["analytics.active"])
        self.assertEqual(
            await inspector.listMaterializedViews(), ["analytics.summary"],
        )
        self.assertEqual(await inspector.listTypes(), [])
        self.assertEqual(await inspector.listDomains(), [])
        self.assertEqual(await inspector.viewCounts(), (1, 2))
        self.assertEqual(await inspector.connectionCount(), 3)
        self.assertEqual(
            inspector.quoteIdentifier("analytics.events"), '"analytics"."events"',
        )
        self.assertEqual(
            inspector._resolveTableName("events", ["analytics.events"]),
            "analytics.events",
        )
        queries = [call.args[0] for call in catalog.select.await_args_list]
        self.assertIn("svv_redshift_tables", queries[0])
        self.assertIn("NOT EXISTS", queries[0])
        self.assertIn("svv_mv_info", queries[0])
        self.assertIn("svv_mv_info", queries[2])
        self.assertIn("COUNT(*)", queries[3])
        self.assertIn("stv_sessions", queries[5])
        self.assertFalse(any("relispartition" in query for query in queries))
        self.assertFalse(any("user_tables" in query for query in queries))

    async def testRedshiftSizeQueriesPreserveQualifiedBindings(self) -> None:
        """Read native sizes without PostgreSQL relation functions.

        Returns
        -------
        None
            Metric queries retain schema bindings and batch all table sizes.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "redshift"
        catalog = Mock()
        catalog.select = AsyncMock(side_effect=[
            [{"bytes": 2097152}], [{"name": "analytics.events", "bytes": 1048576}],
            [{"name": "analytics.events", "bytes": 1048576}],
            [{"name": "analytics.events"}],
        ])
        inspector.connection = catalog
        self.assertEqual(await inspector.databaseSize(), 2097152)
        self.assertEqual(await inspector.tableSize("analytics.events"), 1048576)
        self.assertEqual(await inspector.tableSizes(["analytics.events"]), {
            "analytics.events": 1048576,
        })
        self.assertEqual(
            await inspector._findTableName("analytics.events"), "analytics.events",
        )
        calls = catalog.select.await_args_list
        self.assertIn("size * 1048576", calls[1].args[0])
        self.assertEqual(calls[1].args[1], {"schema": "analytics", "table": "events"})
        self.assertEqual(calls[3].args[1], {
            "kind": "TABLE", "schema": "analytics", "table": "events",
        })

    async def testRedshiftOptionalMetricsHandlePermissionErrors(self) -> None:
        """Keep inspection usable when optional activity and size views are restricted.

        Returns
        -------
        None
            Missing privileges report unknown metrics without hiding coding errors.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "redshift"
        inspector.connection = _FailingMetadataConnection(
            QueryException("restricted"),
        )
        self.assertIsNone(await inspector.databaseSize())
        self.assertIsNone(await inspector.tableSize("analytics.events"))
        self.assertEqual(await inspector.tableSizes(["analytics.events"]), {})
        self.assertIsNone(await inspector.connectionCount())
        inspector.connection = _FailingMetadataConnection(
            TypeError("invalid metadata"),
        )
        with self.assertRaises(TypeError):
            await inspector.databaseSize()

    async def testRedshiftDetailsReportInformationalKeysWithoutIndexes(self) -> None:
        """Read Redshift columns and declared keys without unsupported pg_index queries.

        Returns
        -------
        None
            Column and key output uses the common inspector result shape.
        """
        inspector = DatabaseInspector(self.manager, "reports")
        inspector.driver = "redshift"
        catalog = Mock()
        catalog.select = AsyncMock(side_effect=[
            [{
                "name": "parent_id", "type": "bigint", "nullable": "NO",
                "default_value": None, "primary_key": 1,
            }],
            [{
                "name": "events_parent_fkey", "column_name": "parent_id",
                "ref_table": "analytics.parent", "ref_column": "id",
                "on_delete": "NO ACTION",
            }],
        ])
        inspector.connection = catalog
        columns, indexes, keys = await inspector._serverDetails("analytics.events")
        self.assertTrue(columns[0]["primary"])
        self.assertFalse(columns[0]["nullable"])
        self.assertEqual(indexes, [])
        self.assertEqual(keys[0]["references"], "analytics.parent.id")
        self.assertEqual(catalog.select.await_count, 2)
        for call in catalog.select.await_args_list:
            self.assertEqual(call.args[1], {"schema": "analytics", "table": "events"})
            self.assertNotIn("pg_index", call.args[0])
