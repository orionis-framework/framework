from orionis import aio
from orionis.aio import loop as loop_module
from orionis.aio.loop import Loop
from orionis.test import TestCase

class TestAioPackageExports(TestCase):

    def testAllPublishesOnlyTheLoopManager(self) -> None:
        """
        Publish the loop manager as the single public export.

        Validates that the package surface stays limited to the class the
        framework documents.
        """
        self.assertEqual(aio.__all__, ["Loop"])

    def testLoopIsReExportedByReference(self) -> None:
        """
        Re-export the loop manager defined by the implementation module.

        Validates that the package exposes the very same object instead of
        a copy or a wrapper.
        """
        self.assertIs(aio.Loop, Loop)

    def testPackageNamespaceIsLimitedToTheExportAndTheSubmodule(self) -> None:
        """
        Keep the package namespace free of accidental public names.

        Validates that only the exported class and the implementation
        submodule are reachable from the package.
        """
        public = {name for name in vars(aio) if not name.startswith("_")}
        self.assertEqual(public, {"Loop", "loop"})

    def testSubmoduleIsReachableThroughThePackage(self) -> None:
        """
        Expose the implementation submodule as a package attribute.

        Validates the ``from orionis.aio.loop import Loop`` import used by
        the framework internals.
        """
        self.assertIs(aio.loop, loop_module)
