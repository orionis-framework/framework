# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import importlib
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
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
        """Return the backend class published by the imported module.

        Validates that the helper resolves the attribute instead of the
        module itself.

        Returns
        -------
        None
            No return value.
        """
        backend = import_hasher_backend(
            _INSTALLED_MODULE,
            _INSTALLED_CLASS,
            _PACKAGE,
        )
        self.assertIs(backend, PwdlibArgon2Hasher)

    def testUnknownAttributeIsNotSwallowed(self) -> None:
        """Propagate the failure raised by an unknown backend attribute.

        Validates that a typo in the module coordinates surfaces as a
        plain AttributeError instead of a misleading dependency error.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(AttributeError):
            import_hasher_backend(_INSTALLED_MODULE, "Missing", _PACKAGE)


class TestImportHasherBackendMissingModule(TestCase):
    def testMissingModulePreservesTheOriginalImportError(self) -> None:
        """Preserve the import failure that triggered the translation.

        Validates that the original traceback stays reachable for
        diagnostics.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(MissingHashDependencyException) as captured:
            import_hasher_backend(_ABSENT_MODULE, _INSTALLED_CLASS, _PACKAGE)
        self.assertIsInstance(captured.exception.__cause__, ImportError)

    def testMissingModuleExplainsHowToInstallThePackage(self) -> None:
        """Report the distribution the driver needs to become usable.

        Validate the package name and uv command for both hashing backends.

        Returns
        -------
        None
            No return value.
        """
        for package in ("pwdlib[argon2]", "pwdlib[bcrypt]"):
            with self.assertRaises(MissingHashDependencyException) as captured:
                import_hasher_backend(_ABSENT_MODULE, _INSTALLED_CLASS, package)
            message = str(captured.exception)
            self.assertIn(package, message)
            self.assertIn(f"uv add '{package}'", message)


class TestImportHasherBackendUnavailableBackend(TestCase):
    def setUp(self) -> None:
        """Publish a module that reports itself as unavailable.

        Reproduces the state of an installation where the optional
        backend of a driver is not present.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        workspace = self.enterContext(tempfile.TemporaryDirectory())
        source = Path(workspace) / f"{_UNAVAILABLE_MODULE}.py"
        source.write_text(_UNAVAILABLE_SOURCE, encoding="utf-8")
        self.enterContext(patch.object(sys, "path", [workspace, *sys.path]))
        self.addCleanup(importlib.invalidate_caches)
        self.addCleanup(sys.modules.pop, _UNAVAILABLE_MODULE, None)
        importlib.invalidate_caches()

    def testUnavailableBackendIsReportedAsAMissingDependency(self) -> None:
        """Translate an unavailable backend into a module level failure.

        Validate the uv hint and the error raised by an unavailable backend.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(MissingHashDependencyException) as captured:
            import_hasher_backend(
                _UNAVAILABLE_MODULE,
                _INSTALLED_CLASS,
                _PACKAGE,
            )
        self.assertIsInstance(captured.exception.__cause__, HasherNotAvailable)
        self.assertIn(f"uv add '{_PACKAGE}'", str(captured.exception))
