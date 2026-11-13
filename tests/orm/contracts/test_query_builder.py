# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.query_builder import QueryBuilder
from orionis.test import TestCase
from tests.orm.contracts.test_base_builder import assert_contract_surface


class TestQueryBuilderContract(TestCase):
    """Verify the DB gateway's connection, SQL, and transaction interface."""

    def testSurfaceMatchesTheGatewayImplementation(self) -> None:
        """Match gateway methods and their parameter kinds.

        Returns
        -------
        None
            No return value.
        """
        expected = frozenset(
            {
                "connection",
                "table",
                "beginTransaction",
                "commit",
                "rollback",
                "transaction",
                "getDefaultName",
                "setDefaultName",
                "select",
                "execute",
                "statement",
            },
        )
        assert_contract_surface(self, IQueryBuilder, QueryBuilder, expected)

    def testContractDeclaresEmptySlots(self) -> None:
        """Prevent the gateway interface from adding dynamic instance state.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IQueryBuilder.__dict__.get("__slots__"), ())
