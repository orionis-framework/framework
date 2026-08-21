from orionis import logging as logging_package
from orionis.logging.logger import Logger
from orionis.test import TestCase

class TestLoggingPackage(TestCase):

    def testExportsOnlyTheLoggerSymbol(self) -> None:
        """
        Declare Logger as the only public export of the package.

        Validates that the ``__all__`` contract of ``orionis.logging`` stays
        limited to the single service the framework publishes.
        """
        self.assertEqual(logging_package.__all__, ["Logger"])

    def testExportedNameResolvesToTheImplementation(self) -> None:
        """
        Resolve the exported name to the concrete Logger class.

        Validates that the package alias and the module attribute are the very
        same object, so imports from either path share one implementation.
        """
        self.assertIs(logging_package.Logger, Logger)

    def testEveryDeclaredExportIsImportable(self) -> None:
        """
        Expose every name declared in the export list.

        Validates that ``__all__`` never advertises a symbol missing from the
        package namespace, which would break star imports.
        """
        for name in logging_package.__all__:
            self.assertTrue(hasattr(logging_package, name))
