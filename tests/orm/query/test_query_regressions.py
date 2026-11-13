# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve model policies and SELECT composition through query terminals."""

import inspect
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, get_type_hints
from unittest.mock import patch
from orionis.database.connection_manager import ConnectionManager
from orionis.orm import DateTime, Integer, Model, String
from orionis.orm.contracts.base_builder import IQueryBuilderBase
from orionis.orm.contracts.builder import IModelQueryBuilder
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.contracts.raw_builder import IRawQueryBuilder
from orionis.orm.query import expressions
from orionis.orm.query.base_builder import QueryBuilderBase
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.orm.query.join_clause import JoinClause
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.test import TestCase


if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection


class _ScopedRecord(Model):
    """Represent rows whose owner and deletion policies must survive composition."""

    table = "query_policy_records"
    timestamps = False
    soft_deletes = True
    id = Integer().primary()
    owner = Integer()
    label = String()
    deleted_at = DateTime().nullable()


class TestQueryCompositionRegressions(TestCase):
    """Exercise composition against an isolated SQLite database."""

    async def asyncSetUp(self) -> None:
        """Create independent storage and register cleanup before opening it.

        Returns
        -------
        None
            No return value.
        """
        configuration = {
            "default": "sqlite",
            "connections": {"sqlite": {"driver": "sqlite", "database": ":memory:"}},
        }
        self._manager = ConnectionManager(
            SimpleNamespace(config=lambda _section: configuration),
        )
        self.addAsyncCleanup(self._manager.disconnect)
        self.addCleanup(ConnectionResolver.setManager, ConnectionResolver._manager)
        ConnectionResolver.setManager(self._manager)
        self.enterContext(
            patch.dict(_ScopedRecord.__meta__.global_scopes, {}, clear=True),
        )
        await self._manager.connection().createTable(_ScopedRecord.__meta__.table)
        await self.raw().insert(
            [
                {"id": 1, "owner": 2, "label": "other", "deleted_at": None},
                {"id": 2, "owner": 1, "label": "visible", "deleted_at": None},
                {
                    "id": 3,
                    "owner": 1,
                    "label": "deleted",
                    "deleted_at": datetime(2026, 1, 1, tzinfo=UTC),
                },
            ],
        )

    @staticmethod
    def raw() -> RawQueryBuilder:
        """Return a fresh model-less query over the controlled fixture table.

        Returns
        -------
        RawQueryBuilder
            A raw builder over the isolated policy fixture table.
        """
        return RawQueryBuilder().table(_ScopedRecord.table)

    async def testEmbeddedModelsRetainScopesAndDeletionPolicy(self) -> None:
        """Apply model filters to detached subqueries in every embedding surface.

        Returns
        -------
        None
            No return value.
        """
        _ScopedRecord.addGlobalScope("owner", lambda query: query.where("owner", 1))
        for mode, expected in (
            ("default", [2]),
            ("trashed", [2, 3]),
            ("unscoped", [1, 2]),
        ):
            for surface in ("membership", "exists", "join", "union", "projection"):
                with self.subTest(mode=mode, surface=surface):
                    source = _ScopedRecord.query().select("id")
                    if mode == "trashed":
                        source.withTrashed()
                    elif mode == "unscoped":
                        source.withoutGlobalScopes()
                    outer = self.raw()
                    if surface == "membership":
                        outer.whereIn("id", source)
                    elif surface == "exists":
                        outer.table(_ScopedRecord.table, alias="outer_record")
                        source.whereColumn(
                            "query_policy_records.id",
                            "=",
                            "outer_record.id",
                        )
                        outer.whereExists(source)
                    elif surface == "join":
                        outer.select("query_policy_records.id").joinSub(
                            source,
                            "allowed",
                            "allowed.id",
                            "=",
                            "query_policy_records.id",
                        )
                    elif surface == "union":
                        outer.select("id").where("id", -1).union(source)
                    else:
                        outer.selectSub(source.orderBy("id").limit(1), "selected")
                        result = await outer.first()
                        self.assertEqual(result["selected"], expected[0])
                        self.assertFalse(source._scopes_applied)
                        continue
                    rows = await outer.get()
                    self.assertEqual(sorted(row["id"] for row in rows), expected)
                    self.assertFalse(source._scopes_applied)

    def testUnchangedPlansStayBorrowedWhileCustomHooksArePrepared(self) -> None:
        """Avoid cloning no-op plans while preserving overridden preparation hooks.

        Returns
        -------
        None
            No return value.
        """

        class FilteredRaw(RawQueryBuilder):
            """Apply an owner policy before a raw query is embedded."""

            def _beforeExecute(self) -> None:
                """Add the fixture owner constraint before executing the query.

                Returns
                -------
                None
                    No return value.
                """
                self.where("owner", 1)

        outer = self.raw()
        raw = self.raw().select("id")
        self.assertIs(outer._resolvePlan(raw), raw.toPlan())
        custom = FilteredRaw().table(_ScopedRecord.table).select("id")
        prepared = outer._resolvePlan(custom)
        self.assertIsNot(prepared, custom.toPlan())
        self.assertEqual(len(prepared.wheres), 1)
        self.assertEqual(custom.toPlan().wheres, [])
        model = _ScopedRecord.query().withTrashed()
        original = model.toPlan()
        model._beforeExecute()
        self.assertIs(model.toPlan(), original)
        self.assertTrue(model._scopes_applied)

    async def testFailedScopeCanRetryWithoutLosingPolicy(self) -> None:
        """Leave failed preparation unpublished and apply all filters on retry.

        Returns
        -------
        None
            No return value.
        """
        attempts = 0
        failure = RuntimeError("controlled scope preparation failure")

        def owner_scope(query: ModelQueryBuilder) -> None:
            """Fail the first application after adding its owner condition.

            Parameters
            ----------
            query : ModelQueryBuilder
                Query receiving a controlled owner policy.

            Returns
            -------
            None
                No return value.
            """
            nonlocal attempts
            attempts += 1
            query.where("owner", 1)
            if attempts == 1:
                raise failure

        _ScopedRecord.addGlobalScope("owner", owner_scope)
        query = _ScopedRecord.query()
        original = query.toPlan()
        with self.assertRaises(RuntimeError) as caught:
            await query.get()
        self.assertIs(caught.exception, failure)
        with self.subTest(check="preparation remains unpublished"):
            self.assertIs(query.toPlan(), original)
            self.assertEqual(query.toPlan().wheres, [])
            self.assertFalse(query._scopes_applied)
        with self.subTest(check="retry reapplies every policy"):
            self.assertEqual([model.id for model in await query.get()], [2])
            self.assertEqual(attempts, 2)
            self.assertEqual(len(query.toPlan().wheres), 2)

    async def testExistenceKeepsCompoundAndHavingProjections(self) -> None:
        """Preserve UNION arity and aggregate HAVING semantics in existence probes.

        Returns
        -------
        None
            No return value.
        """
        for kind in ("raw", "model"):
            for shape in ("union", "having"):
                with self.subTest(kind=kind, shape=shape):
                    query = self.raw() if kind == "raw" else _ScopedRecord.withTrashed()
                    if shape == "union":
                        query.select("id", "label").where("id", 1).union(
                            self.raw().select("id", "label").where("id", 2),
                        )
                    else:
                        query.selectRaw("count(*)", alias="total").havingRaw(
                            "count(*) > 1",
                        )
                    self.assertTrue(await query.exists())

    async def testAggregatesUseEveryUnionBranch(self) -> None:
        """Aggregate the complete compound result rather than its first branch.

        Returns
        -------
        None
            No return value.
        """
        for aggregate, expected in (("sum", 6), ("min", 1), ("max", 3), ("avg", 2)):
            with self.subTest(aggregate=aggregate):
                query = (
                    self.raw()
                    .select("id")
                    .whereIn("id", [2, 3])
                    .union(
                        self.raw().select("id").where("id", 1),
                    )
                )
                self.assertEqual(await getattr(query, aggregate)("id"), expected)

    async def testModelQueriesHonorConnectionHooksAndExplicitTargets(self) -> None:
        """Read through the model hook until a query explicitly selects another name.

        Returns
        -------
        None
            No return value.
        """
        primary = self._manager.connection()

        class RoutedRecord(_ScopedRecord):
            """Keep the fixture table while resolving its connection explicitly."""

            table = _ScopedRecord.table

            @classmethod
            def getConnection(cls) -> IConnection:
                """Return the controlled connection without a global resolver.

                Returns
                -------
                IConnection
                    Fixture connection supplied by the model hook.
                """
                return primary

        ConnectionResolver.clear()
        try:
            with self.subTest(terminal="get"):
                self.assertEqual(
                    [record.id for record in await RoutedRecord.orderBy("id").get()],
                    [1, 2],
                )
            with self.subTest(terminal="first"):
                self.assertEqual((await RoutedRecord.orderBy("id").first()).id, 1)
        finally:
            ConnectionResolver.setManager(self._manager)

        self._manager.addConnection(
            "replica",
            {"driver": "sqlite", "database": ":memory:"},
        )
        replica = self._manager.connection("replica")
        await replica.createTable(_ScopedRecord.__meta__.table)
        await (
            self.raw()
            .adoptConnection("replica")
            .insert(
                {
                    "id": 9,
                    "owner": 1,
                    "label": "replica",
                    "deleted_at": None,
                },
            )
        )
        self.assertEqual(
            (await RoutedRecord.query().adoptConnection("replica").first()).id,
            9,
        )


class TestQueryRuntimeAnnotations(TestCase):
    """Resolve public query and expression annotations with the actual types."""

    def testPublicAnnotationsResolveAtRuntime(self) -> None:
        """Resolve concrete, contract, clause and plan hints without custom globals.

        Returns
        -------
        None
            No return value.
        """
        classes = [
            QueryBuilderBase,
            ModelQueryBuilder,
            RawQueryBuilder,
            JoinClause,
            IQueryBuilderBase,
            IModelQueryBuilder,
            IRawQueryBuilder,
            IQueryBuilder,
        ]
        classes.extend(
            value
            for value in vars(expressions).values()
            if inspect.isclass(value) and value.__module__ == expressions.__name__
        )
        for klass in classes:
            with self.subTest(klass=klass.__name__, method="class annotations"):
                get_type_hints(klass)
            for name, descriptor in vars(klass).items():
                method = (
                    descriptor.__func__
                    if isinstance(descriptor, (classmethod, staticmethod))
                    else descriptor
                )
                if inspect.isfunction(method):
                    with self.subTest(klass=klass.__name__, method=name):
                        get_type_hints(method)
