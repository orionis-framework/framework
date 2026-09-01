import importlib
import sys
import tempfile
from pathlib import Path
from pwdlib.exceptions import HasherNotAvailable
from pwdlib.hashers.argon2 import Argon2Hasher as PwdlibArgon2Hasher
from orionis.hashing.exceptions import MissingHashDependencyException
from orionis.hashing.hashers.functions import import_hasher_backend
from orionis.test import TestCase

# Coordinates of a backend that is really installed in the environment.
_INSTALLED_MODULE: str = "pwdlib.hashers.argon2"
_INSTALLED_CLASS: str = "Argon2Hasher"
_PACKAGE: str = "pwdlib[argon2]"

# Module that can never be resolved by the import machinery.
_ABSENT_MODULE: str = "orionis_absent_hashing_backend"

# Module that reports itself as unavailable while being imported.
_UNAVAILABLE_MODULE: str = "orionis_unavailable_hashing_backend"
_UNAVAILABLE_SOURCE: str = (
    "from pwdlib.exceptions import HasherNotAvailable\n"
    "raise HasherNotAvailable('argon2')\n"
)


class TestImportHasherBackendSuccess(TestCase):

    def testReturnsTheRequestedBackendClass(self) -> None:
        """
        Return the backend class published by the imported module.

        Validates that the helper resolves the attribute instead of the
        module itself.
        """
        backend = import_hasher_backend(
            _INSTALLED_MODULE,
            _INSTALLED_CLASS,
            _PACKAGE,
        )
        self.assertIs(backend, PwdlibArgon2Hasher)

    def testDoesNotInstantiateTheBackend(self) -> None:
        """
        Return the class itself and never an instance of it.

        Validates the lazy contract the drivers rely on to stay
        constructible without paying the cost of a backend.
        """
        backend = import_hasher_backend(
            _INSTALLED_MODULE,
            _INSTALLED_CLASS,
            _PACKAGE,
        )
        self.assertIsInstance(backend, type)

    def testUnknownAttributeIsNotSwallowed(self) -> None:
        """
        Propagate the failure raised by an unknown backend attribute.

        Validates that a typo in the module coordinates surfaces as a
        plain AttributeError instead of a misleading dependency error.
        """
        with self.assertRaises(AttributeError):
            import_hasher_backend(_INSTALLED_MODULE, "Missing", _PACKAGE)


class TestImportHasherBackendMissingModule(TestCase):

    def testMissingModuleIsReportedAsAMissingDependency(self) -> None:
        """
        Translate an unresolvable module into a module level failure.

        Validates that callers only have to catch the exception published
        by the hashing module.
        """
        with self.assertRaises(MissingHashDependencyException):
            import_hasher_backend(_ABSENT_MODULE, _INSTALLED_CLASS, _PACKAGE)

    def testMissingModulePreservesTheOriginalImportError(self) -> None:
        """
        Preserve the import failure that triggered the translation.

        Validates that the original traceback stays reachable for
        diagnostics.
        """
        with self.assertRaises(MissingHashDependencyException) as captured:
            import_hasher_backend(_ABSENT_MODULE, _INSTALLED_CLASS, _PACKAGE)
        self.assertIsInstance(captured.exception.__cause__, ImportError)

    def testMissingModuleExplainsHowToInstallThePackage(self) -> None:
        """
        Report the distribution the driver needs to become usable.

        Validates that the message names the package and the command that
        installs it.
        """
        with self.assertRaises(MissingHashDependencyException) as captured:
            import_hasher_backend(_ABSENT_MODULE, _INSTALLED_CLASS, _PACKAGE)
        message = str(captured.exception)
        self.assertIn(_PACKAGE, message)
        self.assertIn(f"pip install {_PACKAGE}", message)


class TestImportHasherBackendUnavailableBackend(TestCase):

    def setUp(self) -> None:
        """
        Publish a module that reports itself as unavailable.

        Reproduces the state of an installation where the optional
        backend of a driver is not present.
        """
        self._workspace = tempfile.TemporaryDirectory()
        source = Path(self._workspace.name) / f"{_UNAVAILABLE_MODULE}.py"
        source.write_text(_UNAVAILABLE_SOURCE, encoding="utf-8")
        sys.path.insert(0, self._workspace.name)
        importlib.invalidate_caches()

    def tearDown(self) -> None:
        """
        Remove the temporary module from the interpreter state.

        Guarantees that neither the import path nor the module cache leak
        into other tests.
        """
        sys.modules.pop(_UNAVAILABLE_MODULE, None)
        if self._workspace.name in sys.path:
            sys.path.remove(self._workspace.name)
        self._workspace.cleanup()

    def testUnavailableBackendIsReportedAsAMissingDependency(self) -> None:
        """
        Translate an unavailable backend into a module level failure.

        Validates the branch that catches the error raised by the backend
        library when its optional dependency is absent.
        """
        with self.assertRaises(MissingHashDependencyException) as captured:
            import_hasher_backend(
                _UNAVAILABLE_MODULE,
                _INSTALLED_CLASS,
                _PACKAGE,
            )
        self.assertIsInstance(captured.exception.__cause__, HasherNotAvailable)
