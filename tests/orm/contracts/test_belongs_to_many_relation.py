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
            Verify the complete many-to-many relation contract.
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
            self, IBelongsToManyRelation, BelongsToManyRelation, expected,
        )

    def testContractDeclaresEmptySlots(self) -> None:
        """Prevent the pivot interface from introducing an instance dictionary.

        Returns
        -------
        None
            Verify the interface declares empty slots.
        """
        self.assertEqual(IBelongsToManyRelation.__dict__.get("__slots__"), ())
