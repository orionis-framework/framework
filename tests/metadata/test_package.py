from orionis import metadata
from orionis.metadata import framework
from orionis.test import TestCase

class TestMetadataPackageExports(TestCase):
    """Re-export contract of the ``orionis.metadata`` package."""

    def testAllMirrorsEveryPublicConstantOfTheModule(self) -> None:
        """
        Re-export every public constant declared by the framework module.

        Validates that adding a constant to ``framework.py`` without
        listing it in ``__all__`` is reported as a failure.
        """
        declared = {name for name in vars(framework) if not name.startswith("_")}
        self.assertEqual(set(metadata.__all__), declared)

    def testAllIsSortedAndFreeOfDuplicates(self) -> None:
        """
        Keep the export list sorted and free of duplicates.

        Validates that the public API stays reviewable at a glance.
        """
        self.assertEqual(metadata.__all__, sorted(set(metadata.__all__)))

    def testEveryExportedNameIsTheObjectDefinedInTheModule(self) -> None:
        """
        Bind every exported name to the object defined in the module.

        Validates that the package re-exports values by reference instead
        of duplicating them.
        """
        for name in metadata.__all__:
            self.assertIs(getattr(metadata, name), getattr(framework, name))

    def testPackageNamespaceIsLimitedToTheExportsAndTheSubmodule(self) -> None:
        """
        Keep the package namespace free of accidental public names.

        Validates that only the exported constants and the ``framework``
        submodule are reachable from the package.
        """
        public = {name for name in vars(metadata) if not name.startswith("_")}
        self.assertEqual(public, set(metadata.__all__) | {"framework"})

    def testSubmoduleIsReachableThroughThePackage(self) -> None:
        """
        Expose the framework submodule as a package attribute.

        Validates the ``from orionis.metadata import framework`` access
        used by the ``about`` command.
        """
        self.assertIs(metadata.framework, framework)
