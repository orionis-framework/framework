# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis.orm.query.expressions import JoinCondition
from orionis.orm.query.join_clause import JoinClause
from orionis.test import TestCase


class TestJoinClause(TestCase):
    """Verify fluent ON accumulation and the compiler's condition ordering."""

    def testAndAndOrConditionsRemainInDeclarationOrder(self) -> None:
        """Accumulate qualified comparisons without changing their connectors.

        Returns
        -------
        None
            No return value.
        """
        join = JoinClause()
        self.assertIs(join.on("posts.user_id", "=", "users.id"), join)
        self.assertIs(join.orOn("posts.editor_id", "=", "users.id"), join)
        self.assertEqual(
            join.conditions(),
            [
                JoinCondition("posts.user_id", "=", "users.id"),
                JoinCondition("posts.editor_id", "=", "users.id", "or"),
            ],
        )

    def testConditionsAreOwnedByTheirJoinClause(self) -> None:
        """Keep condition lists separate and expose each accumulated list.

        Returns
        -------
        None
            No return value.
        """
        first = JoinClause()
        second = JoinClause()
        observed = first.conditions()
        first.on("left.id", "=", "right.id")
        self.assertIs(first.conditions(), observed)
        self.assertEqual(len(observed), 1)
        self.assertEqual(second.conditions(), [])
