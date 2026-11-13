# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis.orm.contracts.belongs_to_many_relation import IBelongsToManyRelation
from orionis.orm.relations.belongs_to_many import BelongsToManyRelation
from orionis.test import TestCase
from tests.orm.contracts.test_base_builder import assert_contract_surface
from tests.orm.contracts.test_relation import RELATION_METHODS


class TestBelongsToManyRelationContract(TestCase):
    """Verify pivot operations preserve the complete relation interface."""

    def testSurfaceMatchesThePivotRelationImplementation(self) -> None:
        """Match pivot mutation methods and inherited query signatures.

        Returns
        -------
        None
            No return value.
        """
        expected = RELATION_METHODS | frozenset(
            {
                "wherePivot",
                "attach",
                "detach",
                "sync",
                "toggle",
            },
        )
        assert_contract_surface(
            self,
            IBelongsToManyRelation,
            BelongsToManyRelation,
            expected,
        )
        self.assertEqual(IBelongsToManyRelation.__dict__.get("__slots__"), ())
