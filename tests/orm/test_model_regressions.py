# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations

from datetime import UTC, datetime
from typing import get_type_hints

from orionis.database.connection import Connection
from orionis.database.connection_manager import ConnectionManager
from orionis.database.migrations.context import migration_connection_scope
from orionis.orm import DateTime, Integer, Model, String
from orionis.orm import attributes, events, metaclass, resolver, soft_deletes
from orionis.orm.query.expressions import DeletePlan
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.test import TestCase
from tests.orm.test_model import _StubApp
from tests.orm.test_state import _ComparisonGuard, _Record


class _Uncopyable:
    """Expose a user value whose snapshot cannot be copied."""

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        """Reject copying independently of the caller's snapshot state.

        Parameters
        ----------
        memo : dict of int to object
            Objects already copied by the active traversal.

        Returns
        -------
        object
            No value because copying always fails.

        Raises
        ------
        ValueError
            If the snapshot tries to copy this value.
        """
        error_msg = f"Cannot copy this value with {len(memo)} memo entries."
        raise ValueError(error_msg)


class TestModelRegressions(TestCase):
    """Protect snapshots, declaration ownership, and successful-write events."""

    def testFailedSnapshotPreservesThePreviousOriginal(self) -> None:
        """Publish a new original snapshot only after copying succeeds.

        Returns
        -------
        None
            No return value.
        """
        record = _Record._newFromDatabase({"id": 1, "name": "before"})
        expected = record.getOriginal()
        record.setAttribute("payload", _Uncopyable())
        with self.assertRaisesRegex(ValueError, "Cannot copy"):
            record.syncOriginal()
        self.assertEqual(record.getOriginal(), expected)

    def testMissingAttributesDoNotCompareValuesAgainstASentinel(self) -> None:
        """Treat a newly assigned attribute as dirty without comparing its value.

        Returns
        -------
        None
            No return value.
        """
        record = _Record()
        value = _ComparisonGuard()
        record.setAttribute("payload", value)
        for operation in (
            record.getDirty,
            record.isDirty,
            lambda: record.isDirty("payload"),
        ):
            with self.subTest(operation=operation):
                self.assertTrue(operation())

    def testReusedColumnDeclarationsKeepEachBoundName(self) -> None:
        """Bind an inline column without renaming another model's declaration.

        Returns
        -------
        None
            No return value.
        """
        declaration = String().nullable()
        original_name = declaration.name

        class _First(Model):
            first = declaration

        class _Abstract(Model):
            __abstract__ = True
            deferred = declaration

        class _Second(_Abstract):
            second = declaration

        self.assertEqual(_First.__meta__.columns["first"].name, "first")
        self.assertEqual(_Second.__meta__.columns["deferred"].name, "deferred")
        self.assertEqual(_Second.__meta__.columns["second"].name, "second")
        self.assertEqual(declaration.name, original_name)
        self.assertTrue(_Second.__meta__.columns["second"].is_nullable)

    async def testMissingRowsDoNotDispatchSuccessfulWriteEvents(self) -> None:
        """Keep post-write events absent when the stored row no longer exists.

        Returns
        -------
        None
            No return value.
        """
        connection = Connection("sqlite", {"driver": "sqlite", "database": ":memory:"})
        self.addAsyncCleanup(connection.disconnect)

        class _Observed(Model):
            id = Integer().primary().autoIncrement()
            name = String()
            deleted_at = DateTime().nullable()
            timestamps = False
            soft_deletes = True

            @classmethod
            def getConnection(cls) -> Connection:
                """Return the database owned by this regression.

                Returns
                -------
                Connection
                    Isolated SQLite connection.
                """
                return connection

        await connection.createTable(_Observed.__meta__.table)
        for operation, expected in (
            ("save", ["saving", "updating"]),
            ("delete", ["deleting"]),
            ("forceDelete", ["deleting"]),
            ("restore", ["restoring"]),
        ):
            with self.subTest(operation=operation):
                _Observed.flushEvents()
                record = await _Observed.create(
                    {
                        "name": "before",
                        "deleted_at": datetime(2026, 1, 1, tzinfo=UTC),
                    },
                )
                await connection.delete(DeletePlan(table=_Observed.__meta__.table))
                record.name = "after"
                seen = []
                for event in metaclass.MODEL_EVENTS:
                    _Observed.registerEvent(
                        event,
                        lambda _model, name=event, observed=seen: observed.append(name),
                    )
                self.assertFalse(await getattr(record, operation)())
                self.assertEqual(seen, expected)

    async def testGatewayQueriesKeepTheirOwningManager(self) -> None:
        """Execute fluent queries against their gateway after resolver replacement.

        Returns
        -------
        None
            No return value.
        """
        self.addCleanup(
            setattr,
            ConnectionResolver,
            "_manager",
            ConnectionResolver._manager,
        )
        first_manager = ConnectionManager(_StubApp())
        second_manager = ConnectionManager(_StubApp())
        self.addAsyncCleanup(first_manager.disconnect)
        self.addAsyncCleanup(second_manager.disconnect)
        for manager, label in ((first_manager, "first"), (second_manager, "second")):
            for name in ("sqlite", "replica"):
                connection = manager.connection(name)
                await connection.createTable(_Record.__meta__.table)
                await connection.execute(
                    "INSERT INTO records (id, name) VALUES (:id, :name)",
                    {"id": 1, "name": f"{label}-{name}"},
                )
        ConnectionResolver.setManager(first_manager)
        gateway = QueryBuilder(first_manager)
        original = gateway.table("records")
        ConnectionResolver.setManager(second_manager)
        for query, expected in (
            (original, "first-sqlite"),
            (original.clone(), "first-sqlite"),
            (gateway.table("records"), "first-sqlite"),
            (gateway.connection("replica").table("records"), "first-replica"),
            (gateway.table("records").connection("replica"), "first-replica"),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(await query.value("name"), expected)

        other_gateway = QueryBuilder(second_manager)
        with migration_connection_scope(first_manager.connection("replica")):
            deferred = other_gateway.table("records")
            explicit = other_gateway.table("records", connection="sqlite")
        self.assertEqual(await deferred.value("name"), "first-replica")
        self.assertEqual(await deferred.clone().value("name"), "first-replica")
        self.assertEqual(await explicit.value("name"), "second-sqlite")
        self.assertEqual(
            await other_gateway.table("records").value("name"),
            "second-sqlite",
        )

    async def testHydratedModelsPersistOnTheirSelectedConnection(self) -> None:
        """Keep instance writes on the connection that supplied the stored row.

        Returns
        -------
        None
            No return value.
        """
        self.addCleanup(
            setattr,
            ConnectionResolver,
            "_manager",
            ConnectionResolver._manager,
        )
        manager = ConnectionManager(_StubApp())
        self.addAsyncCleanup(manager.disconnect)
        ConnectionResolver.setManager(manager)
        for name in ("sqlite", "replica"):
            connection = manager.connection(name)
            await connection.createTable(_Record.__meta__.table)
            await connection.execute(
                "INSERT INTO records (id, name) VALUES (:id, :name)",
                {"id": 1, "name": name},
            )
        record = await _Record.query().adoptConnection("replica").firstOrFail()
        self.assertEqual(record.name, "replica")
        record.name = "updated"
        self.assertTrue(await record.save())
        self.assertEqual(
            await manager.connection("replica").select("SELECT name FROM records"),
            [{"name": "updated"}],
        )
        self.assertTrue(await record.delete())
        self.assertEqual(
            await manager.connection("replica").select("SELECT name FROM records"),
            [],
        )
        self.assertEqual(
            await manager.connection("sqlite").select("SELECT name FROM records"),
            [{"name": "sqlite"}],
        )

    def testPublicRuntimeAnnotationsResolveToTheirDeclaredTypes(self) -> None:
        """Resolve public ORM annotations without caller-provided namespaces.

        Returns
        -------
        None
            No return value.
        """
        for target in (
            attributes.get_cast_handler,
            attributes.serialize_for_storage,
            events.EventsMixin.registerEvent,
            metaclass.ModelMetadata,
            resolver.ConnectionResolver.setManager,
            resolver.ConnectionResolver.connection,
            soft_deletes.SoftDeletesMixin._performSoftDelete,
            Model,
            Model.getConnection,
            Model.all,
            Model.addGlobalScope,
            QueryBuilder.table,
        ):
            with self.subTest(target=target):
                self.assertTrue(get_type_hints(target))
