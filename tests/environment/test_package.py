from types import ModuleType
from orionis import environment as environment_package
from orionis.environment import Env
from orionis.environment.functions import env
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# TestEnvironmentPackageSurface
# ---------------------------------------------------------------------------

class TestEnvironmentPackageSurface(TestCase):
    """Verify the environment package exports."""

    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """Declare the two documented public exports.

        Returns
        -------
        None
            Assertions verify the published export list.
        """
        self.assertEqual(environment_package.__all__, ["Env", "env"])

    def testReExportsTheEnvFacade(self) -> None:
        """Preserve the exported ``Env`` facade identity.

        Returns
        -------
        None
            Assertions compare the export with its defining class.
        """
        self.assertIs(environment_package.Env, Env)

    def testReExportsTheEnvHelperFunction(self) -> None:
        """Preserve the exported ``env`` helper identity.

        Returns
        -------
        None
            Assertions compare the export with its defining function.
        """
        self.assertIs(environment_package.env, env)

    def testNoExportShadowsASubmodule(self) -> None:
        """Keep public exports distinct from their implementation modules.

        Returns
        -------
        None
            Assertions reject module objects among the exports.
        """
        for name in environment_package.__all__:
            self.assertNotIsInstance(getattr(environment_package, name), ModuleType)

    def testExposesNoUndocumentedPublicObjects(self) -> None:
        """Keep every non-module public attribute inside ``__all__``.

        Returns
        -------
        None
            Assertions compare the resolved surface with declared exports.
        """
        exported = {
            name
            for name in dir(environment_package)
            if not name.startswith("_")
            and not isinstance(getattr(environment_package, name), ModuleType)
        }
        self.assertEqual(exported, set(environment_package.__all__))
