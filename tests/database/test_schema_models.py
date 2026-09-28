from __future__ import annotations
from unittest.mock import AsyncMock, Mock
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.migrations.context import migration_connection_scope
from orionis.database.schema.schema import Schema
from orionis.orm.model import Model
from orionis.orm.schema.constraints import TableIndex, UniqueConstraint
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, String
from orionis.test import TestCase

class _CurrentModel(Model):
    table = "schema_models"
    connection = "model_connection"
    timestamps = False
    id = Integer().primary().autoIncrement()
    name = String(80)

class _DefaultModel(Model):
    table = "schema_defaults"
    timestamps = False
    id = Integer().primary().autoIncrement()

class TestModelSchemaSelection(TestCase):
    """Select table metadata and connections without database reflection."""

    def setUp(self) -> None:
        """Capture the table definition passed to each schema operation."""
        self.connection = Mock()
        self.connection.createTable = AsyncMock(return_value=True)
        self.connection.dropTable = AsyncMock(return_value=True)
        self.manager = Mock(spec=IConnectionManager)
        self.manager.connection.return_value = self.connection
        self.schema = Schema(self.manager)

    async def testCreateFromDefinitionPassesTheOriginalMetadata(self) -> None:
        """Reuse the versioned schema object for DDL compilation."""
        definition = _CurrentModel.__meta__.table
        self.assertTrue(await self.schema.createFromDefinition(definition))
        self.connection.createTable.assert_awaited_once_with(definition)
        self.manager.connection.assert_called_once_with(None)

    async def testCreateFromModelUsesItsDeclaredConnection(self) -> None:
        """Resolve the model connection when the schema has no override."""
        self.assertTrue(await self.schema.createFromModel(_CurrentModel))
        self.connection.createTable.assert_awaited_once_with(
            _CurrentModel.__meta__.table,
        )
        self.manager.connection.assert_called_once_with("model_connection")

    async def testExplicitConnectionOverridesTheModelConnection(self) -> None:
        """Honor an explicitly selected schema connection."""
        await self.schema.connection("override").createFromModel(_CurrentModel)
        self.manager.connection.assert_called_once_with("override")

    async def testExplicitDefaultOverridesTheModelConnection(self) -> None:
        """Select the manager default even when the model names a connection."""
        await self.schema.connection(None).createFromModel(_CurrentModel)
        self.manager.connection.assert_called_once_with(None)
        with self.assertRaises(ValueError):
            self.schema.connection("override")

    async def testCreateFromModelRejectsAbstractAndNonModelClasses(self) -> None:
        """Report invalid model arguments before accessing a connection."""
        for invalid in (Model, object, _CurrentModel()):
            with self.subTest(invalid=invalid), self.assertRaises(TypeError):
                await self.schema.createFromModel(invalid)
        self.manager.connection.assert_not_called()

    async def testMigrationScopeBindsUnqualifiedSchemaCalls(self) -> None:
        """Create and drop tables on the connection owned by a migration."""
        target = Mock()
        target.createTable = AsyncMock(return_value=True)
        target.dropTable = AsyncMock(return_value=True)
        with migration_connection_scope(target):
            await self.schema.createFromModel(_DefaultModel)
            await self.schema.createFromDefinition(_CurrentModel.__meta__.table)
            await self.schema.drop("schema_defaults")
        self.assertEqual(target.createTable.await_count, 2)
        target.dropTable.assert_awaited_once_with(
            name="schema_defaults", schema=None,
        )
        self.manager.connection.assert_not_called()

    async def testExplicitSchemaSelectionOverridesTheMigrationScope(self) -> None:
        """Keep explicitly selected schema connections authoritative."""
        with migration_connection_scope(Mock()):
            await self.schema.connection(None).createFromModel(_DefaultModel)
        self.manager.connection.assert_called_once_with(None)

    async def testQualifiedTableNameRetainsBothParts(self) -> None:
        """Pass the database schema separately from the table name."""
        await self.schema.drop("reporting.entries")
        self.connection.dropTable.assert_awaited_once_with(
            name="entries", schema="reporting",
        )

    async def testMalformedTableNamesNeverReachTheConnection(self) -> None:
        """Reject names that would otherwise drop a truncated table name."""
        for name in ("", ".table", "schema.", "one.two.three"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                await self.schema.drop(name)
        self.connection.dropTable.assert_not_awaited()

    async def testFluentCreationStillCollectsColumnsAndConstraints(self) -> None:
        """Keep the existing context-manager declaration API functional."""
        async with self.schema.create("users") as table:
            table.integer("id").primary()
            table.string("name", 80).unique()
            table.timestamps()
        definition = self.connection.createTable.await_args.args[0]
        self.assertEqual(
            definition.columnNames(), ("id", "name", "created_at", "updated_at"),
        )
        self.assertTrue(definition.columns["name"].is_unique)
        self.assertTrue(definition.columns["created_at"].is_nullable)

class _SchemaApp:
    """Provide a private in-memory SQLite database for schema integration."""

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Return the connection configuration requested by the manager."""
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }

class TestVersionedSchemaIntegration(TestCase):
    """Replay a historical schema after the active model adopts a new one."""

    async def testModelAndMigrationShareOneVersionedDefinition(self) -> None:
        """Create the historical table independently from current model changes."""
        initial = TableDefinition(
            name="versioned_users",
            columns={
                "id": Integer().primary().autoIncrement(),
                "name": String(80),
            },
            unique_constraints=(UniqueConstraint(columns=("name",)),),
            indexes=(TableIndex(columns=("name",), name="users_name_index"),),
        )
        current = TableDefinition(
            name=initial.name,
            columns={**initial.columns, "email": String(120).nullable()},
        )

        class VersionedUser(Model):
            table_definition = current
            timestamps = False

        manager = ConnectionManager(_SchemaApp())
        schema = Schema(manager)
        try:
            await schema.createFromDefinition(initial)
            connection = manager.connection()
            columns = await connection.select("PRAGMA table_info(versioned_users)")
            self.assertEqual([row["name"] for row in columns], ["id", "name"])
            self.assertIs(VersionedUser.__meta__.table, current)
            self.assertTrue(VersionedUser.__meta__.table.hasColumn("email"))
            indexes = await connection.select("PRAGMA index_list(versioned_users)")
            self.assertIn("users_name_index", {row["name"] for row in indexes})
            self.assertTrue(any(row["unique"] for row in indexes))
            await schema.drop(initial.name)
            await schema.createFromModel(VersionedUser)
            columns = await connection.select("PRAGMA table_info(versioned_users)")
            self.assertEqual(
                [row["name"] for row in columns], ["id", "name", "email"],
            )
        finally:
            await manager.disconnect()
