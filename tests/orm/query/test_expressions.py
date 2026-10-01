from dataclasses import FrozenInstanceError, fields
from orionis.orm.query.expressions import (
    AggregateClause,
    AggregateFunction,
    DeletePlan,
    InsertPlan,
    JoinCondition,
    JoinExpression,
    JoinType,
    LockMode,
    OrderClause,
    RawExpression,
    SelectPlan,
    SortDirection,
    SubQueryColumn,
    UnionClause,
    UpdatePlan,
    WhereClause,
)
from orionis.orm.schema.table import TableDefinition
from orionis.test import TestCase

class TestQueryExpressions(TestCase):
    """Verify plan ownership and the intermediate query representation."""

    def testClonePreservesMetadataAndDetachesEveryClauseList(self) -> None:
        """Preserve select metadata while copying all mutable clause lists.

        Returns
        -------
        None
            Verify list independence and intentionally shared clause objects.
        """
        table = TableDefinition("users")
        subquery = SelectPlan(TableDefinition("posts"), columns=("id",))
        clause = WhereClause("id", value=1)
        join = JoinExpression(
            JoinType.LEFT,
            subquery,
            alias="p",
            conditions=[JoinCondition("users.id", second="p.id")],
        )
        plan = SelectPlan(
            table,
            alias="u",
            joins=[join],
            columns=(
                "id",
                RawExpression("count(*)"),
                SubQueryColumn(subquery, "total"),
            ),
            wheres=[clause],
            orders=[OrderClause("id", SortDirection.DESC)],
            groups=["id"],
            havings=[WhereClause("id", operator=">", value=0)],
            limit_value=5,
            offset_value=2,
            aggregate=AggregateClause(AggregateFunction.COUNT),
            distinct=True,
            lock=LockMode.UPDATE,
            unions=[UnionClause(subquery, all_rows=True)],
        )
        duplicate = plan.clone()
        self.assertIsNot(duplicate, plan)
        for field in fields(SelectPlan):
            original = getattr(plan, field.name)
            copied = getattr(duplicate, field.name)
            self.assertEqual(copied, original, field.name)
            if isinstance(original, list):
                self.assertIsNot(copied, original, field.name)
                copied.clear()
                self.assertTrue(original, field.name)
        self.assertIs(duplicate.table, table)
        self.assertIs(duplicate.columns, plan.columns)
        self.assertIs(plan.wheres[0], clause)
        self.assertIs(plan.joins[0], join)

    def testFreshPlansNeverShareMutableContainers(self) -> None:
        """Keep default SELECT and mutation containers independent.

        Returns
        -------
        None
            Verify mutating one fresh plan cannot change another plan.
        """
        table = TableDefinition("users")
        for plan_type in (SelectPlan, InsertPlan, UpdatePlan, DeletePlan):
            first = plan_type(table)
            second = plan_type(table)
            for field in fields(plan_type):
                value = getattr(first, field.name)
                if isinstance(value, (dict, list)):
                    self.assertIsNot(value, getattr(second, field.name), field.name)
            self.assertFalse(hasattr(first, "__dict__"))

    def testRawExpressionsPreserveBindingsAndRejectMetadataMutation(self) -> None:
        """Keep developer SQL, bindings, and aliases in a frozen fragment.

        Returns
        -------
        None
            Verify fragment bindings are independent and metadata is immutable.
        """
        fragment = RawExpression("amount + :increment", {"increment": 2}, "total")
        self.assertEqual(fragment.bindings, {"increment": 2})
        self.assertEqual(fragment.alias, "total")
        first = RawExpression("first")
        second = RawExpression("second")
        first.bindings["value"] = 7
        self.assertEqual(second.bindings, {})
        attribute = "sql"
        with self.assertRaises(FrozenInstanceError):
            setattr(fragment, attribute, "different")
