# ruff: noqa: PT009, PT027
# Native assertions observe persisted SQLite values and the public plan compiler.
"""Exercise UUID predicate/storage consistency using real temporary SQLite files."""

from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.exc import ArgumentError
from orionis.database.compiler import SQLCompiler
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import (
    DeletePlan,
    InsertPlan,
    JoinCondition,
    JoinExpression,
    JoinType,
    SelectPlan,
    UpdatePlan,
    WhereClause,
    WhereType,
)
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, PickleType, String, Uuid

if TYPE_CHECKING:
    from orionis.orm.schema.column import ColumnDefinition

_FIRST = UUID("41ef4d39-9188-48f3-a5cb-638946c1e001")
_SECOND = UUID("41ef4d39-9188-48f3-a5cb-638946c1e002")
_THIRD = UUID("41ef4d39-9188-48f3-a5cb-638946c1e003")


class TestUuidPredicateRegressions(unittest.TestCase):
    """Verify UUID predicates against each declared storage representation."""

    def setUp(self) -> None:
        """Build committed textual UUID rows in a fresh SQLite file.

        Returns
        -------
        None
            Register cleanup and prepare committed rows for each test.
        """
        temporary = tempfile.TemporaryDirectory(prefix="orionis-uuid-predicate-")
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "owned.sqlite"
        self.engine = create_engine("sqlite:///" + path.as_posix())
        self.addCleanup(self.engine.dispose)
        self.compiler = SQLCompiler(driver="sqlite")
        self.table = self._table(
            "uuid_records",
            {"id": String(36).primary(), "name": String(80)},
        )
        with self.engine.begin() as connection:
            connection.execute(self.compiler.compileCreateTable(self.table))
            connection.execute(
                self.compiler.compileInsert(
                    InsertPlan(
                        table=self.table,
                        values=[
                            {"id": str(key), "name": f"row-{index}"}
                            for index, key in enumerate((_FIRST, _SECOND, _THIRD))
                        ],
                    ),
                ),
            )

    @staticmethod
    def _table(
        name: str,
        columns: dict[str, ColumnDefinition],
    ) -> TableDefinition:
        """Bind column names and build a public table definition.

        Parameters
        ----------
        name : str
            Name of the temporary table.
        columns : dict[str, ColumnDefinition]
            Column definitions indexed by their bound names.

        Returns
        -------
        TableDefinition
            Table metadata with its primary key bound to ``id``.
        """
        for column_name, column in columns.items():
            column.name = column_name
        return TableDefinition(name=name, columns=columns, primary_key="id")

    def _select(self, plan: SelectPlan) -> list[dict[str, object]]:
        """Read committed rows through a separate connection.

        Parameters
        ----------
        plan : SelectPlan
            Query plan to compile and execute.

        Returns
        -------
        list[dict[str, object]]
            Rows mapped by their selected column names.
        """
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    self.compiler.compileSelect(plan),
                ).mappings()
            ]

    def testEqualityMatchesUuidStoredWithHyphens(self) -> None:
        """Compare an actual UUID object against the committed VARCHAR value.

        Returns
        -------
        None
            Verify that the stored row matches its UUID predicate.
        """
        rows = self._select(
            SelectPlan(
                table=self.table,
                wheres=[WhereClause(column="id", value=_FIRST)],
            ),
        )
        self.assertEqual(rows, [{"id": str(_FIRST), "name": "row-0"}])

    def testMembershipAndExclusionUseTheStoredRepresentation(self) -> None:
        """Check both expanding IN bindings and NOT IN against persisted data.

        Returns
        -------
        None
            Verify membership and exclusion against committed UUID text.
        """
        members = self._select(
            SelectPlan(
                table=self.table,
                wheres=[
                    WhereClause(
                        column="id",
                        where_type=WhereType.IN,
                        value=(_FIRST, _THIRD),
                    ),
                ],
            ),
        )
        excluded = self._select(
            SelectPlan(
                table=self.table,
                wheres=[
                    WhereClause(
                        column="id",
                        where_type=WhereType.NOT_IN,
                        value=(_SECOND,),
                    ),
                ],
            ),
        )
        self.assertEqual({row["id"] for row in members}, {str(_FIRST), str(_THIRD)})
        self.assertEqual({row["id"] for row in excluded}, {str(_FIRST), str(_THIRD)})

    def testNestedAliasedPredicateUsesItsDeclaredTextColumn(self) -> None:
        """Resolve a nested UUID condition through an aliased source.

        Returns
        -------
        None
            Verify the row selected through the nested alias predicate.
        """
        rows = self._select(
            SelectPlan(
                table=self.table,
                alias="u",
                wheres=[
                    WhereClause(
                        column="",
                        where_type=WhereType.NESTED,
                        value=[
                            WhereClause(column="u.id", value=_SECOND),
                            WhereClause(column="u.name", value="row-1"),
                        ],
                    ),
                ],
            ),
        )
        self.assertEqual(rows, [{"id": str(_SECOND), "name": "row-1"}])

    def testJoinedSourcePredicateUsesTheJoinedColumnType(self) -> None:
        """Resolve a UUID predicate through the joined column type.

        Returns
        -------
        None
            Verify selection through the joined textual UUID column.
        """
        related = self._table(
            "uuid_related",
            {"id": Integer().primary(), "owner_id": String(36)},
        )
        with self.engine.begin() as connection:
            connection.execute(self.compiler.compileCreateTable(related))
            connection.execute(
                self.compiler.compileInsert(
                    InsertPlan(
                        table=related,
                        values=[{"id": 1, "owner_id": str(_THIRD)}],
                    ),
                ),
            )
        rows = self._select(
            SelectPlan(
                table=self.table,
                alias="u",
                columns=("u.name",),
                joins=[
                    JoinExpression(
                        join_type=JoinType.INNER,
                        table=related,
                        alias="p",
                        conditions=[JoinCondition(first="u.id", second="p.owner_id")],
                    ),
                ],
                wheres=[WhereClause(column="p.owner_id", value=_THIRD)],
            ),
        )
        self.assertEqual(rows, [{"name": "row-2"}])

    def testUpdateAndDeleteMatchTextKeysAndCommit(self) -> None:
        """Apply UUID predicates on writes and verify from a new connection.

        Returns
        -------
        None
            Verify committed updates and deletions from another connection.
        """
        with self.engine.begin() as connection:
            updated = connection.execute(
                self.compiler.compileUpdate(
                    UpdatePlan(
                        table=self.table,
                        values={"name": "changed"},
                        wheres=[WhereClause(column="id", value=_FIRST)],
                    ),
                ),
            )
            self.assertEqual(updated.rowcount, 1)
            deleted = connection.execute(
                self.compiler.compileDelete(
                    DeletePlan(
                        table=self.table,
                        wheres=[
                            WhereClause(
                                column="id",
                                where_type=WhereType.IN,
                                value=(_SECOND, _THIRD),
                            ),
                        ],
                    ),
                ),
            )
            self.assertEqual(deleted.rowcount, 2)
        self.assertEqual(
            self._select(SelectPlan(table=self.table)),
            [{"id": str(_FIRST), "name": "changed"}],
        )

    def testDeclaredUuidColumnsRetainTheirOwnProcessor(self) -> None:
        """Keep UUID semantic types intact for native and emulated declarations.

        Returns
        -------
        None
            Verify both UUID declarations retain their typed processors.
        """
        for native in (False, True):
            with self.subTest(native_uuid=native):
                table = self._table(
                    "typed_uuid_" + str(int(native)),
                    {"id": Uuid(native_uuid=native).primary()},
                )
                with self.engine.begin() as connection:
                    connection.execute(self.compiler.compileCreateTable(table))
                    connection.execute(
                        self.compiler.compileInsert(
                            InsertPlan(
                                table=table,
                                values=[{"id": _FIRST}, {"id": _SECOND}],
                            ),
                        ),
                    )
                self.assertEqual(
                    self._select(
                        SelectPlan(
                            table=table,
                            wheres=[WhereClause(column="id", value=_FIRST)],
                        ),
                    ),
                    [{"id": _FIRST}],
                )
                self.assertEqual(
                    self._select(
                        SelectPlan(
                            table=table,
                            wheres=[
                                WhereClause(
                                    column="id",
                                    where_type=WhereType.IN,
                                    value=(_SECOND,),
                                ),
                            ],
                        ),
                    ),
                    [{"id": _SECOND}],
                )

    def testBetweenAndNotBetweenDoNotMutateTheirBounds(self) -> None:
        """Use UUID range bounds in the stored textual order without rewriting plans.

        Returns
        -------
        None
            Verify both ranges and preserve the supplied bounds.
        """
        bounds = [_FIRST, _SECOND]
        clause = WhereClause(column="id", where_type=WhereType.BETWEEN, value=bounds)
        plan = SelectPlan(table=self.table, wheres=[clause])
        rows = self._select(plan)
        excluded = self._select(
            SelectPlan(
                table=self.table,
                wheres=[
                    WhereClause(
                        column="id",
                        where_type=WhereType.NOT_BETWEEN,
                        value=bounds,
                    ),
                ],
            ),
        )
        self.assertEqual({row["id"] for row in rows}, {str(_FIRST), str(_SECOND)})
        self.assertEqual({row["id"] for row in excluded}, {str(_THIRD)})
        self.assertIs(clause.value, bounds)
        self.assertEqual(bounds, [_FIRST, _SECOND])

    def testMixedMembershipPreservesCallerValuesAndClause(self) -> None:
        """Normalize only UUID elements and retain the caller's list and NULL.

        Returns
        -------
        None
            Verify mixed values and preserve the supplied list and clause.
        """
        values = [_FIRST, str(_THIRD), None]
        clause = WhereClause(column="id", where_type=WhereType.IN, value=values)
        plan = SelectPlan(table=self.table, wheres=[clause])
        first = self._select(plan)
        again = self._select(plan)
        self.assertEqual({row["id"] for row in first}, {str(_FIRST), str(_THIRD)})
        self.assertEqual(first, again)
        self.assertIs(clause.value, values)
        self.assertEqual(values, [_FIRST, str(_THIRD), None])
        self.assertIs(values[0], _FIRST)

    def testMembershipSubqueryRetainsItsExecutablePlan(self) -> None:
        """Keep an IN subquery as SQL rather than treating it as bound values.

        Returns
        -------
        None
            Verify subquery execution and preserve its query plan.
        """
        subquery = SelectPlan(
            table=self.table,
            alias="s",
            columns=("s.id",),
            wheres=[WhereClause(column="s.name", value="row-1")],
        )
        clause = WhereClause(column="id", where_type=WhereType.IN, value=subquery)
        rows = self._select(SelectPlan(table=self.table, wheres=[clause]))
        self.assertEqual(rows, [{"id": str(_SECOND), "name": "row-1"}])
        self.assertIs(clause.value, subquery)

    def testMalformedMembershipStringStillRaises(self) -> None:
        """Reject a scalar string supplied as an IN sequence.

        Returns
        -------
        None
            Verify that scalar membership values raise a query error.
        """
        plan = SelectPlan(
            table=self.table,
            wheres=[
                WhereClause(column="id", where_type=WhereType.IN, value=str(_FIRST)),
            ],
        )
        with self.assertRaises((ArgumentError, QueryException)):
            self.compiler.compileSelect(plan)

    def testPickledUuidPreservesThePickleProcessor(self) -> None:
        """Preserve UUID objects stored in trusted fixture pickle.

        Returns
        -------
        None
            Verify that pickled UUID values retain their typed processor.
        """
        table = self._table("pickled_uuid", {"id": PickleType().primary()})
        with self.engine.begin() as connection:
            connection.execute(self.compiler.compileCreateTable(table))
            connection.execute(
                self.compiler.compileInsert(
                    InsertPlan(table=table, values=[{"id": _FIRST}]),
                ),
            )
        rows = self._select(
            SelectPlan(table=table, wheres=[WhereClause(column="id", value=_FIRST)]),
        )
        self.assertEqual(rows, [{"id": _FIRST}])
        members = self._select(
            SelectPlan(
                table=table,
                wheres=[
                    WhereClause(column="id", where_type=WhereType.IN, value=(_FIRST,)),
                ],
            ),
        )
        self.assertEqual(members, [{"id": _FIRST}])


if __name__ == "__main__":
    unittest.main()
