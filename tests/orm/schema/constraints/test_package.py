from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "CompositeForeignKey": (
        "orionis.orm.schema.constraints.composite_foreign_key",
        "CompositeForeignKey",
    ),
    "ForeignReference": (
        "orionis.orm.schema.constraints.foreign_reference",
        "ForeignReference",
    ),
    "TableIndex": ("orionis.orm.schema.constraints.table_index", "TableIndex"),
    "UniqueConstraint": (
        "orionis.orm.schema.constraints.unique_constraint",
        "UniqueConstraint",
    ),
}

class TestSchemaConstraintsPackage(TestCase):
    """Verify the orionis.orm.schema.constraints public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.schema.constraints", EXPECTED_EXPORTS)
