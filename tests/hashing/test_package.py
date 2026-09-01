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
        """
        Declare exactly the documented public exports.

        Validates that ``__all__`` stays in sync with the manager and the
        drivers the rest of the framework imports from this package.
        """
        self.assertEqual(hashing_package.__all__, _PUBLIC_SURFACE)

    def testReExportsTheManagerAndBothDrivers(self) -> None:
        """
        Bind every exported name to its concrete implementation.

        Validates that the re-exports point at the real classes instead of
        shadowing aliases.
        """
        self.assertIs(hashing_package.HashManager, HashManager)
        self.assertIs(hashing_package.Argon2Hasher, Argon2Hasher)
        self.assertIs(hashing_package.BcryptHasher, BcryptHasher)

    def testNoExportShadowsASubmodule(self) -> None:
        """
        Keep every export free of collisions with a submodule name.

        Validates that no public name is silently rebound by the import
        machinery, which would make the shadowed submodule unreachable
        through attribute access.
        """
        for name in hashing_package.__all__:
            self.assertNotIsInstance(getattr(hashing_package, name), ModuleType)

    def testExposesNoUndocumentedPublicObjects(self) -> None:
        """
        Keep every non-module public attribute inside ``__all__``.

        Validates that no helper or imported symbol leaks into the package
        namespace without being declared as part of the public API.
        """
        exported = {
            name
            for name, value in vars(hashing_package).items()
            if not name.startswith("_") and not isinstance(value, ModuleType)
        }
        self.assertEqual(exported, set(hashing_package.__all__))
