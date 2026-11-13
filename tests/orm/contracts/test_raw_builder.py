# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
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
            No return value.
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
            No return value.
        """
        self.assertEqual(IRawQueryBuilder.__dict__.get("__slots__"), ())
