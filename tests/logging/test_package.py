# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis import logging as logging_package
from orionis.logging.logger import Logger
from orionis.test import TestCase


class TestLoggingPackage(TestCase):
    def testExportsOnlyTheLoggerSymbol(self) -> None:
        """Declare Logger as the only public export of the package.

        Validates that the ``__all__`` contract of ``orionis.logging`` stays
        limited to the single service the framework publishes.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(logging_package.__all__, ["Logger"])

    def testExportedNameResolvesToTheImplementation(self) -> None:
        """Resolve the exported name to the concrete Logger class.

        Validates that the package alias and the module attribute are the very
        same object, so imports from either path share one implementation.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(logging_package.Logger, Logger)
