# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise database compilation with local engines and controlled metadata."""

import inspect
from typing import get_type_hints

from sqlalchemy import create_engine

from orionis.database import dialect, redshift
from orionis.database.compiler import SQLCompiler
from orionis.database.connection import Connection
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import (
    InsertPlan,
    JoinCondition,
    JoinExpression,
    JoinType,
    OrderClause,
    SelectPlan,
    SortDirection,
    SubQueryColumn,
    UnionClause,
    WhereClause,
    WhereType,
)
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, String
from orionis.test import TestCase


class TestCompilationRegressions(TestCase):
    """Preserve query semantics and connection values without remote providers."""

    def testPublicAnnotationsResolveAtRuntime(self) -> None:
        """Resolve public compiler, dialect and installed Redshift signatures."""
        targets = [
            method
            for name, method in inspect.getmembers(SQLCompiler, inspect.isfunction)
            if not name.startswith("_") or name == "__init__"
        ]
        targets.extend(
            method
            for name, method in inspect.getmembers(dialect, inspect.isfunction)
            if not name.startswith("_") and method.__module__ == dialect.__name__
        )
        if redshift.RedshiftDialect is not None:
            targets.append(redshift.RedshiftDialect.hasTable)
        for method in targets:
            with self.subTest(method=method.__qualname__):
                self.assertIn("return", get_type_hints(method))

    def testEngineUrlsPreserveSignificantPasswordCharacters(self) -> None:
        """Preserve whitespace and empty passwords in both URL dialect modes."""
        for driver in ("mysql", "pgsql", "sqlserver", "oracle", "redshift"):
            for password in (" \tcredential-value\n ", ""):
                for synchronous in (False, True):
                    for dsn in (
                        (None, "controlled-service") if driver == "oracle" else (None,)
                    ):
                        with self.subTest(driver=driver, sync=synchronous, dsn=dsn):
                            config = {
                                "driver": driver,
                                "username": "fixture",
                                "password": password,
                                "dsn": dsn,
                            }
                            original = config.copy()
                            url = dialect.build_engine_url(config, sync=synchronous)
                            self.assertEqual(url.password, password)
                            self.assertEqual(config, original)

    async def testBatchInsertRejectsAnyUnknownColumnShape(self) -> None:
        """Keep unknown bindings out of parameterized multi-row insertion."""
        table = TableDefinition(
            name="items",
            columns={
                "id": Integer().primary().autoIncrement(),
                "name": String().nullable(),
            },
        )
        for row in ({"unknown": 1}, {"id": 1, "unknown": 2}):
            with self.subTest(columns=tuple(row)):
                plan = InsertPlan(table=table, values=[row.copy(), row.copy()])
                self.assertFalse(SQLCompiler.supportsBatchInsert(plan))
                if "id" in plan.values[1]:
                    plan.values[1]["id"] = 2
                connection = Connection(
                    "fixture",
                    {"driver": "sqlite", "database": ":memory:"},
                )
                self.addAsyncCleanup(connection.disconnect)
                await connection.createTable(table)
                with self.assertRaises(QueryException):
                    await connection.insert(plan)
                self.assertEqual(await connection.select(SelectPlan(table)), [])

    def testNestedUnionPlansRetainEveryBranch(self) -> None:
        """Execute nested unions through IN, JOIN, scalar and EXISTS contexts."""
        engine = create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        table = TableDefinition(name="numbers", columns={"id": Integer().primary()})
        compiler = SQLCompiler(driver="sqlite")
        with engine.begin() as connection:
            connection.execute(compiler.compileCreateTable(table))
            connection.execute(
                compiler.compileInsert(InsertPlan(table, [{"id": 1}, {"id": 2}])),
            )
            for context in ("in", "join", "scalar", "exists"):
                with self.subTest(context=context):
                    first = SelectPlan(
                        table=table,
                        alias="inside",
                        columns=("id",),
                        wheres=[
                            WhereClause("id", value=-1 if context == "exists" else 1),
                        ],
                    )
                    second = SelectPlan(
                        table=table,
                        alias="alternative",
                        columns=("id",),
                        wheres=[WhereClause("id", value=2)],
                    )
                    first.unions.append(UnionClause(second))
                    plan = SelectPlan(
                        table=table,
                        alias="outside",
                        columns=("outside.id",),
                    )
                    if context == "in":
                        plan.wheres.append(WhereClause("id", WhereType.IN, value=first))
                    elif context == "join":
                        plan.joins.append(
                            JoinExpression(
                                JoinType.INNER,
                                first,
                                "combined",
                                [JoinCondition("outside.id", "=", "combined.id")],
                            ),
                        )
                    elif context == "scalar":
                        first.orders.append(OrderClause("id", SortDirection.DESC))
                        first.limit_value = 1
                        plan.columns = (SubQueryColumn(first, "maximum"),)
                    else:
                        second.wheres.append(
                            WhereClause(
                                "alternative.id",
                                WhereType.COLUMN,
                                value="outside.id",
                            ),
                        )
                        plan.wheres.append(
                            WhereClause("", WhereType.EXISTS, value=first),
                        )
                    actual = list(
                        connection.execute(compiler.compileSelect(plan)).scalars(),
                    )
                    expected = (
                        [2, 2]
                        if context == "scalar"
                        else [2]
                        if context == "exists"
                        else [1, 2]
                    )
                    self.assertEqual(sorted(actual), expected)

    def testForeignPlaceholdersRetainEveryReferencedColumn(self) -> None:
        """Resolve separate foreign keys to one target before its declaration."""
        compiler = SQLCompiler()
        child = TableDefinition(
            name="children",
            columns={
                "parent_id": Integer().foreign("parents.id"),
                "parent_code": String().foreign("parents.code"),
            },
        )
        rendered = str(compiler.compileCreateTable(child))
        self.assertIn("REFERENCES parents (id)", rendered)
        self.assertIn("REFERENCES parents (code)", rendered)
