from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "IModelQueryBuilder": ("orionis.orm.contracts.builder", "IModelQueryBuilder"),
}

class TestContractsPackage(TestCase):
    """Verify the orionis.orm.contracts public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.contracts", EXPECTED_EXPORTS)
