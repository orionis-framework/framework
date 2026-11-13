# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis.orm.contracts.relation import IRelation
from orionis.orm.relations.relation import Relation
from orionis.test import TestCase
from tests.orm.contracts.test_base_builder import assert_contract_surface
from tests.orm.contracts.test_builder import MODEL_METHODS

RELATION_METHODS = MODEL_METHODS | frozenset(
    {
        "addConstraints",
        "addEagerConstraints",
        "getResults",
        "getEager",
        "match",
    },
)


class TestRelationContract(TestCase):
    """Verify relation templates extend model queries without dynamic state."""

    def testSurfaceMatchesTheRelationTemplate(self) -> None:
        """Match relation hooks and all inherited model query methods.

        Returns
        -------
        None
            No return value.
        """
        assert_contract_surface(self, IRelation, Relation, RELATION_METHODS)
        self.assertEqual(IRelation.__dict__.get("__slots__"), ())
