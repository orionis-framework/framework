from types import ModuleType
from orionis import environment as environment_package
from orionis.environment.facade import Env
from orionis.environment.functions import env
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# TestEnvironmentPackageSurface
# ---------------------------------------------------------------------------

class TestEnvironmentPackageSurface(TestCase):

    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """
        Declare exactly the two documented public exports.

        Validates that ``__all__`` stays in sync with the facade and the
        helper the rest of the framework imports from this package.
        """
        self.assertEqual(environment_package.__all__, ["Env", "env"])

    def testReExportsTheEnvFacade(self) -> None:
        """
        Re-export the very same ``Env`` facade object.

        Validates that importing from the package root yields the class
        defined in ``orionis.environment.facade`` and not a copy.
        """
        self.assertIs(environment_package.Env, Env)

    def testReExportsTheEnvHelperFunction(self) -> None:
        """
        Re-export the very same ``env`` helper function.

        Validates that importing from the package root yields the function
        defined in ``orionis.environment.functions``.
        """
        self.assertIs(environment_package.env, env)

    def testNoExportShadowsASubmodule(self) -> None:
        """
        Keep every export free of collisions with a submodule name.

        Validates that no public name is silently rebound by the import
        machinery, which would make the shadowed submodule unreachable
        through attribute access.
        """
        for name in environment_package.__all__:
            self.assertNotIsInstance(getattr(environment_package, name), ModuleType)

    def testExposesNoUndocumentedPublicObjects(self) -> None:
        """
        Keep every non-module public attribute inside ``__all__``.

        Validates that no helper or imported symbol leaks into the package
        namespace without being declared as part of the public API.
        """
        exported = {
            name
            for name, value in vars(environment_package).items()
            if not name.startswith("_") and not isinstance(value, ModuleType)
        }
        self.assertEqual(exported, set(environment_package.__all__))
