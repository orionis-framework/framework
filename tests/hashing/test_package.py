# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from types import ModuleType
from orionis import hashing as hashing_package
from orionis.hashing.hash_manager import HashManager
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase

# Names the package promises to its consumers.
_PUBLIC_SURFACE: list[str] = ["Argon2Hasher", "BcryptHasher", "HashManager"]


class TestHashingPackageSurface(TestCase):
    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """Declare exactly the documented public exports.

        Validates that ``__all__`` stays in sync with the manager and the
        drivers the rest of the framework imports from this package.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(hashing_package.__all__, _PUBLIC_SURFACE)

    def testReExportsTheManagerAndBothDrivers(self) -> None:
        """Bind every exported name to its concrete implementation.

        Validates that the re-exports point at the real classes instead of
        shadowing aliases.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(hashing_package.HashManager, HashManager)
        self.assertIs(hashing_package.Argon2Hasher, Argon2Hasher)
        self.assertIs(hashing_package.BcryptHasher, BcryptHasher)

    def testExposesNoUndocumentedPublicObjects(self) -> None:
        """Keep every non-module public attribute inside ``__all__``.

        Inspect the advertised surface without assuming deferred symbols
        already exist in the package namespace. Resolve each advertised
        attribute to detect helpers accidentally exposed by ``__dir__``.

        Returns
        -------
        None
            No return value.
        """
        exported = {
            name
            for name in dir(hashing_package)
            if not name.startswith("_")
            and not isinstance(getattr(hashing_package, name), ModuleType)
        }
        self.assertEqual(exported, set(hashing_package.__all__))
