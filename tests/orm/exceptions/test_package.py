from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "InvalidQueryException": ("orionis.orm.exceptions", "InvalidQueryException"),
    "MassAssignmentException": ("orionis.orm.exceptions", "MassAssignmentException"),
    "ModelNotFoundException": ("orionis.orm.exceptions", "ModelNotFoundException"),
    "OrmConfigurationException": (
        "orionis.orm.exceptions",
        "OrmConfigurationException",
    ),
    "OrmException": ("orionis.orm.exceptions", "OrmException"),
    "RelationNotFoundException": (
        "orionis.orm.exceptions",
        "RelationNotFoundException",
    ),
    "ScopeNotFoundException": ("orionis.orm.exceptions", "ScopeNotFoundException"),
}

class TestExceptionsPackage(TestCase):
    """Verify the orionis.orm.exceptions public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.exceptions", EXPECTED_EXPORTS)
