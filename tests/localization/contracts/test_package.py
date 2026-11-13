# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis.localization import contracts
from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.contracts.manager import ILocalizationManager
from orionis.localization.contracts.repository import ITranslationRepository
from orionis.localization.contracts.translator import ITranslator
from orionis.test import TestCase

# Public surface published by orionis.localization.contracts.
_EXPECTED_EXPORTS: tuple[str, ...] = (
    "ILocalizationManager",
    "ITranslationLoader",
    "ITranslationRepository",
    "ITranslator",
)


class TestLocalizationContractsPackage(TestCase):
    """Validate the public surface of the contracts package."""

    def testAllDeclaresEveryContract(self) -> None:
        """Publish exactly the four localization contracts.

        Validates that the package aggregates every interface consumers
        may depend on.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(tuple(contracts.__all__), _EXPECTED_EXPORTS)

    def testExportsReuseTheDefiningModules(self) -> None:
        """Re-export the very interfaces declared by each module.

        Validates that isinstance checks behave identically regardless
        of the import path used.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(contracts.ITranslationLoader, ITranslationLoader)
        self.assertIs(contracts.ITranslationRepository, ITranslationRepository)
        self.assertIs(contracts.ITranslator, ITranslator)
        self.assertIs(contracts.ILocalizationManager, ILocalizationManager)
