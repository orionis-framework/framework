from __future__ import annotations
from unittest.mock import patch
from orionis.database.connection_manager import ConnectionManager
from orionis.orm.exceptions import InvalidQueryException
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Boolean, Integer, String
from orionis.support.facades.db import DB
from orionis.test import TestCase

class _StubApp:
    """Minimal application stub exposing the database configuration."""

    def config(self, key: str) -> dict:  # noqa: ARG002
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": ":memory:",
                    "prefix": "",
                },
            },
        }

def _users_table() -> TableDefinition:
    """Build the physical "users" table used by every test."""
    columns = {
        "id": Integer().primary().autoIncrement(),
        "name": String(),
        "active": Boolean(),
    }
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name="users", columns=columns, primary_key="id")


def _posts_table() -> TableDefinition:
    """Build the physical "posts" table used by the join test."""
    columns = {
        "id": Integer().primary().autoIncrement(),
        "user_id": Integer(),
        "title": String(),
    }
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name="posts", columns=columns, primary_key="id")


class TestRawQueryBuilder(TestCase):
    """
    Integration tests for ``DB.table()`` against a real sqlite connection.

    ``RawQueryBuilder`` never sees the schema created here: it only knows
    the table name, exercising the compiler's schemaless column support.
    """

    async def asyncSetUp(self) -> None:
        """Wire an isolated in-memory manager and create both tables."""
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        facade = patch.object(DB, "_pinned_instance", QueryBuilder(self._manager))
        facade.start()
        self.addCleanup(facade.stop)
        connection = self._manager.connection()
        await connection.createTable(_users_table())
        await connection.createTable(_posts_table())

    async def asyncTearDown(self) -> None:
        """Dispose the manager and clear the resolver after each test."""
        await self._manager.disconnect()
        ConnectionResolver.clear()

    async def testInsertAndGetReturnPlainDictionaries(self) -> None:
        """
        Insert a row and read it back as a plain dictionary.

        Validates the model-less insert/get round trip.
        """
        await DB.table("users").insert({"name": "John", "active": True})
        rows = await DB.table("users").get()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "John")

    async def testWhereFiltersRows(self) -> None:
        """
        Filter rows by an equality condition.

        Validates that ``where()`` narrows the result set.
        """
        await DB.table("users").insert(
            [
                {"name": "John", "active": True},
                {"name": "Jane", "active": False},
            ],
        )
        rows = await DB.table("users").where("active", True).get()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "John")

    async def testFirstReturnsNoneWithoutMatches(self) -> None:
        """
        Return ``None`` from ``first()`` when nothing matches.

        Validates the empty-result path.
        """
        row = await DB.table("users").where("name", "Ghost").first()
        self.assertIsNone(row)

    async def testCountReturnsMatchingRows(self) -> None:
        """
        Count rows matching a condition without fetching them.

        Validates the aggregate terminal.
        """
        await DB.table("users").insert(
            [
                {"name": "a", "active": True},
                {"name": "b", "active": True},
                {"name": "c", "active": False},
            ],
        )
        count = await DB.table("users").where("active", True).count()
        self.assertEqual(count, 2)

    async def testUpdateAndDeleteAffectMatchingRows(self) -> None:
        """
        Update then delete a row through the raw builder.

        Validates both mutation terminals end to end.
        """
        await DB.table("users").insert({"name": "John", "active": True})
        affected = (
            await DB.table("users").where("name", "John").update({"active": False})
        )
        self.assertEqual(affected, 1)
        deleted = await DB.table("users").where("name", "John").delete()
        self.assertEqual(deleted, 1)

    async def testJoinAcrossTwoRawTables(self) -> None:
        """
        Join two model-less tables using qualified projected columns.

        Validates that ``join()`` reuses the JoinExpression compiler
        support without either side declaring a schema upfront.
        """
        await DB.table("users").insert({"name": "John", "active": True})
        await DB.table("posts").insert({"user_id": 1, "title": "Hello"})

        rows = await (
            DB.table("users")
            .join("posts", "users.id", "=", "posts.user_id")
            .select("users.name", "posts.title")
            .get()
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Hello")

    async def testAliasAndOrderByWork(self) -> None:
        """
        Order rows through an aliased table reference.

        Validates that ``alias=`` on ``DB.table()`` reaches the compiler.
        """
        await DB.table("users").insert(
            [
                {"name": "B", "active": True},
                {"name": "A", "active": True},
            ],
        )
        rows = await DB.table("users", alias="u").orderBy("name").get()
        self.assertEqual([row["name"] for row in rows], ["A", "B"])

    async def testInsertWithoutValuesRaises(self) -> None:
        """
        Reject an insert call carrying no rows.

        Validates the same guard used by ``ModelQueryBuilder``.
        """
        with self.assertRaises(InvalidQueryException):
            await DB.table("users").insert([])
