from __future__ import annotations
from typing import ClassVar
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock
from orionis.database.entities.result import InsertResult
from orionis.orm import DateTime, Integer, Model, String
from orionis.orm.attributes import serialize_for_storage
from orionis.orm.exceptions import OrmConfigurationException
from orionis.orm.schema.table import TableDefinition


class _Record(Model):
    id = Integer().primary()
    name = String()
    timestamps = False


class _ComparisonGuard:
    """Reject comparisons to an attribute outside the requested selection."""

    def __ne__(self, other: object) -> bool:
        """Raise if the caller evaluates this attribute."""
        error_msg = f"Unexpected comparison with {type(other).__name__}."
        raise AssertionError(error_msg)


class TestModelHotPaths(TestCase):
    """Exercise attribute state and serialization without database access."""

    def testSelectedDirtyCheckDoesNotCompareUnrequestedAttributes(self) -> None:
        """Inspect only the requested attributes, including missing keys."""
        record = _Record._newFromDatabase({"id": 1, "name": "before"})
        record.setAttribute("unrelated", _ComparisonGuard())
        self.assertFalse(record.isDirty("name", "missing"))
        record.name = "after"
        self.assertTrue(record.isDirty("missing", "name"))

    def testDirtyCheckStopsAtFirstChange(self) -> None:
        """Return after the first changed attribute without comparing the rest."""
        record = _Record({"name": "changed"})
        record.setAttribute("unrelated", _ComparisonGuard())
        self.assertTrue(record.isDirty())

    def testMissingAndNoneRemainDistinct(self) -> None:
        """Track newly assigned null values and ignore absent attributes."""
        record = _Record()
        self.assertFalse(record.isDirty("name"))
        record.name = None
        self.assertTrue(record.isDirty("name"))
        record.syncOriginal()
        self.assertTrue(record.isClean())

    def testSerializationReturnsIndependentMapping(self) -> None:
        """Keep serialization result edits outside the attribute store."""
        record = _Record({"name": "original"})
        result = record.toDict()
        result["name"] = "changed"
        self.assertEqual(record.name, "original")
        values = {"name": "original", "unknown": {"nested": True}}
        stored = serialize_for_storage(record.__meta__, values)
        self.assertEqual(stored, values)
        self.assertIsNot(stored, values)

    def testSharedSchemaRetainsItsTableAndConstraints(self) -> None:
        """Adopt the same versioned table used by schema migrations."""
        definition = TableDefinition(
            name="shared_records", schema="example",
            columns={"key": Integer().primary(), "name": String()},
            primary_key="key", comment="Shared schema version one",
        )

        class _Shared(Model):
            table_definition = definition

        class _Descendant(_Shared):
            pass

        self.assertIs(_Shared.__meta__.table, definition)
        self.assertIs(_Descendant.__meta__.table, definition)
        self.assertEqual(_Shared.__meta__.primary_key, "key")
        self.assertEqual(_Shared({"name": "valid"}).name, "valid")

    def testSharedSchemaRejectsConflictingDeclarations(self) -> None:
        """Reject duplicate columns, table names and primary keys."""
        definition = TableDefinition(
            name="records", columns={"id": Integer().primary()},
        )
        for overrides in (
            {"id": Integer()}, {"table": "other"}, {"primary_key": "other"},
            {"table_definition": "invalid"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(
                OrmConfigurationException,
            ):
                type("Invalid", (Model,), {"table_definition": definition, **overrides})

    def testSoftDeleteInheritanceDoesNotModifyParentSchema(self) -> None:
        """Keep a child nullable delete column isolated from its parent."""
        class _Parent(Model):
            id = Integer().primary()
            deleted_at = DateTime()

        class _SoftChild(_Parent):
            soft_deletes = True

        self.assertFalse(_Parent.__meta__.columns["deleted_at"].is_nullable)
        self.assertTrue(_SoftChild.__meta__.columns["deleted_at"].is_nullable)

    def testSharedSoftDeleteSchemaRequiresNullableColumn(self) -> None:
        """Reject invalid shared schemas without modifying historical definitions."""
        definition = TableDefinition(
            name="records",
            columns={"id": Integer().primary(), "deleted_at": DateTime()},
        )
        with self.assertRaises(OrmConfigurationException):
            type("Invalid", (Model,), {
                "table_definition": definition, "soft_deletes": True,
            })
        self.assertFalse(definition.columns["deleted_at"].is_nullable)


class TestModelPersistenceRouting(IsolatedAsyncioTestCase):
    """Exercise instance persistence using an overridable connection resolver."""

    async def testWritesUseDeclaredConnectionHookAndOneTimestamp(self) -> None:
        """Route all writes through the hook and share creation timestamps."""
        connection = AsyncMock()
        connection.insert.return_value = InsertResult(row_count=1, last_insert_id=7)
        connection.update.return_value = 1
        connection.delete.return_value = 1

        class _Routed(Model):
            id = Integer().primary()
            name = String()
            created_at = DateTime()
            updated_at = DateTime()
            calls: ClassVar[int] = 0

            @classmethod
            def getConnection(cls) -> AsyncMock:
                """Return the connection assigned to this model."""
                cls.calls += 1
                return connection

        record = await _Routed.create({"name": "initial"})
        self.assertEqual(record.id, 7)
        self.assertEqual(record.created_at, record.updated_at)
        self.assertTrue(await record.update({"name": "updated"}))
        self.assertEqual(record.getChanges()["name"], "updated")
        self.assertTrue(record.isClean())
        self.assertTrue(await record.delete())
        self.assertEqual(_Routed.calls, 3)

    async def testInheritedListenersRunOncePerRegistration(self) -> None:
        """Preserve explicit duplicates without multiplying inherited listeners."""
        class _Ancestor(_Record):
            pass

        seen = []
        listener = seen.append
        _Ancestor.registerEvent("saving", listener)
        _Ancestor.registerEvent("saving", listener)

        class _Left(_Ancestor):
            pass

        class _Right(_Ancestor):
            pass

        class _Diamond(_Left, _Right):
            pass

        class _Descendant(_Diamond):
            pass

        record = _Descendant()
        await record.fireEvent("saving")
        self.assertEqual(seen, [record, record])

    async def testFlushedListenersStayAbsentFromDescendants(self) -> None:
        """Keep cleared inherited listeners out of newly declared descendants."""
        class _Ancestor(_Record):
            pass

        _Ancestor.registerEvent("saving", lambda _model: False)

        class _Parent(_Ancestor):
            pass

        _Parent.flushEvents("saving")

        class _Descendant(_Parent):
            pass

        self.assertTrue(await _Descendant().fireEvent("saving"))
        self.assertFalse(await _Ancestor().fireEvent("saving"))

    async def testListenersRegisteredDuringDispatchWaitUntilNextEvent(self) -> None:
        """Dispatch an immutable listener snapshot while registration changes."""
        class _Observed(_Record):
            pass

        seen = []

        def register_during_dispatch(record: Model) -> None:
            """Append the next listener during an existing dispatch."""
            seen.append("first")
            type(record).registerEvent("saved", lambda _model: seen.append("next"))

        _Observed.registerEvent("saved", register_during_dispatch)
        await _Observed().fireEvent("saved")
        self.assertEqual(seen, ["first"])
        await _Observed().fireEvent("saved")
        self.assertEqual(seen, ["first", "first", "next"])
