from orionis import localization
from orionis.localization import exceptions as exceptions_module
from orionis.localization import loader as loader_module
from orionis.localization import manager as manager_module
from orionis.localization import repository as repository_module
from orionis.localization import translator as translator_module
from orionis.test import TestCase

# Public surface published by orionis.localization.
_EXPECTED_EXPORTS: tuple[str, ...] = (
    "InvalidLocaleException",
    "LocalizationManager",
    "TranslationException",
    "TranslationFileNotFoundException",
    "TranslationLoader",
    "TranslationRepository",
    "TranslationSyntaxException",
    "Translator",
)

class TestLocalizationPackageExports(TestCase):
    """Validate the public surface of the localization package."""

    def testAllDeclaresTheDocumentedSurface(self) -> None:
        """
        Publish exactly the documented public names.

        Validates that no symbol is silently added to or removed from
        the package contract.
        """
        self.assertEqual(tuple(localization.__all__), _EXPECTED_EXPORTS)

    def testAllIsSortedAndFreeOfDuplicates(self) -> None:
        """
        Keep the export list sorted and unique.

        Validates that the package contract stays readable and that no
        name is exported twice.
        """
        exported = list(localization.__all__)
        self.assertEqual(exported, sorted(exported))
        self.assertEqual(len(exported), len(set(exported)))

    def testEveryExportedNameIsReachable(self) -> None:
        """
        Resolve every exported name from the package namespace.

        Validates that the declared contract never advertises a symbol
        the package does not actually expose.
        """
        for name in localization.__all__:
            self.assertTrue(hasattr(localization, name), name)

    def testExportsReuseTheDefiningModules(self) -> None:
        """
        Re-export the very objects declared by each submodule.

        Validates that the package aggregates the implementation
        modules instead of shadowing them with copies.
        """
        self.assertIs(localization.TranslationLoader, loader_module.TranslationLoader)
        self.assertIs(
            localization.TranslationRepository,
            repository_module.TranslationRepository,
        )
        self.assertIs(localization.Translator, translator_module.Translator)
        self.assertIs(
            localization.LocalizationManager,
            manager_module.LocalizationManager,
        )

    def testExceptionExportsReuseTheExceptionsModule(self) -> None:
        """
        Re-export the exception hierarchy from its defining module.

        Validates that consumers catching a package-level exception
        catch the very same class raised internally.
        """
        self.assertIs(
            localization.TranslationException,
            exceptions_module.TranslationException,
        )
        self.assertIs(
            localization.InvalidLocaleException,
            exceptions_module.InvalidLocaleException,
        )
        self.assertIs(
            localization.TranslationFileNotFoundException,
            exceptions_module.TranslationFileNotFoundException,
        )
        self.assertIs(
            localization.TranslationSyntaxException,
            exceptions_module.TranslationSyntaxException,
        )
