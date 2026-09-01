from types import ModuleType
from orionis import console as console_package
from orionis.console.args.argument import Argument
from orionis.console.debug.dumper import Dumper
from orionis.console.dynamic.progress_bar import ProgressBar
from orionis.console.output.console import Console
from orionis.test import TestCase

# Names the package promises to its consumers.
_PUBLIC_SURFACE: list[str] = ["Argument", "Console", "Dumper", "ProgressBar"]


class TestConsolePackageSurface(TestCase):

    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """
        Declare exactly the documented public exports.

        Validates that ``__all__`` stays in sync with the helpers the rest
        of the framework imports from this package.
        """
        self.assertEqual(console_package.__all__, _PUBLIC_SURFACE)

    def testReExportsEveryPublicHelper(self) -> None:
        """
        Bind every exported name to its concrete implementation.

        Validates that the re-exports point at the real classes instead of
        shadowing aliases.
        """
        self.assertIs(console_package.Argument, Argument)
        self.assertIs(console_package.Console, Console)
        self.assertIs(console_package.Dumper, Dumper)
        self.assertIs(console_package.ProgressBar, ProgressBar)

    def testNoExportShadowsASubmodule(self) -> None:
        """
        Keep every export free of collisions with a submodule name.

        Validates that no public name is silently rebound by the import
        machinery, which would make the shadowed submodule unreachable
        through attribute access.
        """
        for name in console_package.__all__:
            self.assertNotIsInstance(getattr(console_package, name), ModuleType)

    def testExposesNoUndocumentedPublicObjects(self) -> None:
        """
        Keep every non-module public attribute inside ``__all__``.

        Validates that no helper or imported symbol leaks into the package
        namespace without being declared as part of the public API.
        """
        exported = {
            name
            for name, value in vars(console_package).items()
            if not name.startswith("_") and not isinstance(value, ModuleType)
        }
        self.assertEqual(exported, set(console_package.__all__))
