from types import ModuleType

import orionis.background as package
from orionis.background import BackgroundTask, BackgroundTasks
from orionis.background.task import BackgroundTask as TaskImplementation
from orionis.background.tasks import BackgroundTasks as TasksImplementation
from orionis.test import TestCase

# Public surface promised by the package.
_EXPORTED_NAMES: frozenset[str] = frozenset({"BackgroundTask", "BackgroundTasks"})

class TestBackgroundPackageExports(TestCase):
    """Validate the public surface exposed by ``orionis.background``."""

    def testDeclaresTheExpectedPublicNames(self) -> None:
        """
        Declare exactly the documented exports.

        Validates that ``__all__`` lists the two classes that make up the
        supported package surface.
        """
        self.assertEqual(frozenset(package.__all__), _EXPORTED_NAMES)

    def testExportsAreSortedAndUnique(self) -> None:
        """
        Keep the export list sorted and free of duplicates.

        Validates that ``__all__`` is a stable, canonical listing instead
        of an accidental accumulation of names.
        """
        self.assertEqual(package.__all__, sorted(_EXPORTED_NAMES))

    def testDoesNotLeakAdditionalPublicNames(self) -> None:
        """
        Hide implementation modules from the package namespace.

        Validates that no public attribute beyond the declared exports is
        reachable from the package root.
        """
        public_names = {
            name
            for name, value in vars(package).items()
            if not name.startswith("_") and not isinstance(value, ModuleType)
        }
        self.assertEqual(public_names, _EXPORTED_NAMES)

    def testReExportsTheImplementationClasses(self) -> None:
        """
        Re-export the very classes defined by the implementation modules.

        Validates that the package root and the concrete modules resolve
        to the same objects, so both import paths are interchangeable.
        """
        self.assertIs(BackgroundTask, TaskImplementation)
        self.assertIs(BackgroundTasks, TasksImplementation)
