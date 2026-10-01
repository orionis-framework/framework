from orionis.orm.contracts.builder import IModelQueryBuilder
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.test import TestCase
from tests.orm.contracts.test_base_builder import BASE_METHODS, assert_contract_surface

MODEL_METHODS = BASE_METHODS | frozenset(
    {
        "withRelations",
        "load",
        "get",
        "first",
        "firstOrFail",
        "find",
        "findOrFail",
        "value",
        "pluck",
        "paginate",
    },
)

class TestModelQueryBuilderContract(TestCase):
    """Verify model terminals extend the shared query-language contract."""

    def testSurfaceMatchesModelTerminalsAndSharedMethods(self) -> None:
        """Match model-specific terminals and inherited query signatures.

        Returns
        -------
        None
            Verify the complete model query contract and concrete surface.
        """
        assert_contract_surface(
            self, IModelQueryBuilder, ModelQueryBuilder, MODEL_METHODS,
        )

    def testContractDeclaresEmptySlots(self) -> None:
        """Keep the model query interface free of instance dictionaries.

        Returns
        -------
        None
            Verify the interface declares empty slots.
        """
        self.assertEqual(IModelQueryBuilder.__dict__.get("__slots__"), ())
