"""Verify ORM schema package behavior."""

from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "ColumnDefinition": ("orionis.orm.schema.column.definition", "ColumnDefinition"),
    "ColumnOptions": ("orionis.orm.schema.column.options", "ColumnOptions"),
}


class TestSchemaColumnPackage(TestCase):
    """Verify the orionis.orm.schema.column public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            No return value.
        """
        assert_package_exports(self, "orionis.orm.schema.column", EXPECTED_EXPORTS)
