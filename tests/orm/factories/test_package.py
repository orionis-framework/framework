from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "Factory": ("orionis.orm.factories.factory", "Factory"),
    "FactoryConcurrencyException": (
        "orionis.orm.factories.exceptions",
        "FactoryConcurrencyException",
    ),
    "FactoryConfigurationException": (
        "orionis.orm.factories.exceptions",
        "FactoryConfigurationException",
    ),
    "FactoryDefinitionException": (
        "orionis.orm.factories.exceptions",
        "FactoryDefinitionException",
    ),
    "FactoryDependencyException": (
        "orionis.orm.factories.exceptions",
        "FactoryDependencyException",
    ),
    "FactoryException": ("orionis.orm.factories.exceptions", "FactoryException"),
    "FactoryPersistenceException": (
        "orionis.orm.factories.exceptions",
        "FactoryPersistenceException",
    ),
    "Fake": ("orionis.orm.factories.fake", "Fake"),
    "OptionalFake": ("orionis.orm.factories.fake", "OptionalFake"),
    "Sequence": ("orionis.orm.factories.sequence", "Sequence"),
    "UniqueFake": ("orionis.orm.factories.fake", "UniqueFake"),
}

class TestFactoriesPackage(TestCase):
    """Verify the orionis.orm.factories public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.factories", EXPECTED_EXPORTS)
