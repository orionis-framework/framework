from orionis.orm.contracts.raw_builder import IRawQueryBuilder
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.test import TestCase
from tests.orm.contracts.test_base_builder import BASE_METHODS, assert_contract_surface

class TestRawQueryBuilderContract(TestCase):
    """Verify raw row terminals share the same fluent query contract."""

    def testSurfaceMatchesRawTerminalsAndSharedMethods(self) -> None:
        """Match raw table selection and row terminal signatures.

        Returns
        -------
        None
            Verify the complete model-less query builder interface.
        """
        expected = BASE_METHODS | frozenset(
            {
                "connection",
                "table",
                "get",
                "first",
                "value",
                "pluck",
                "paginate",
            },
        )
        assert_contract_surface(self, IRawQueryBuilder, RawQueryBuilder, expected)

    def testContractDeclaresEmptySlots(self) -> None:
        """Keep raw query implementations dictionary-free through the interface.

        Returns
        -------
        None
            Verify the interface declares its own empty slots.
        """
        self.assertEqual(IRawQueryBuilder.__dict__.get("__slots__"), ())
