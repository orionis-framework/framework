from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "Collection": ("orionis.orm.collections.collection", "Collection"),
    "ModelCollection": ("orionis.orm.collections.collection", "ModelCollection"),
    "Paginator": ("orionis.orm.collections.paginator", "Paginator"),
}

class TestCollectionsPackage(TestCase):
    """Verify the orionis.orm.collections public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.collections", EXPECTED_EXPORTS)
