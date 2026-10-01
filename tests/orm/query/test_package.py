from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "AggregateClause": ("orionis.orm.query.expressions", "AggregateClause"),
    "AggregateFunction": ("orionis.orm.query.expressions", "AggregateFunction"),
    "DeletePlan": ("orionis.orm.query.expressions", "DeletePlan"),
    "InsertPlan": ("orionis.orm.query.expressions", "InsertPlan"),
    "ModelQueryBuilder": ("orionis.orm.query.builder", "ModelQueryBuilder"),
    "OrderClause": ("orionis.orm.query.expressions", "OrderClause"),
    "SelectPlan": ("orionis.orm.query.expressions", "SelectPlan"),
    "SortDirection": ("orionis.orm.query.expressions", "SortDirection"),
    "UpdatePlan": ("orionis.orm.query.expressions", "UpdatePlan"),
    "WhereClause": ("orionis.orm.query.expressions", "WhereClause"),
    "WhereType": ("orionis.orm.query.expressions", "WhereType"),
}

class TestQueryPackage(TestCase):
    """Verify the orionis.orm.query public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.query", EXPECTED_EXPORTS)
