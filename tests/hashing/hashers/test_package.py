from orionis.hashing import hashers as hashers_package
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase


class TestHashersPackage(TestCase):

    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """
        Declare exactly the two shipped drivers as public exports.

        Validates that the helper module stays private to the package.
        """
        self.assertEqual(
            hashers_package.__all__,
            ["Argon2Hasher", "BcryptHasher"],
        )

    def testReExportsBothDrivers(self) -> None:
        """
        Bind every exported name to its driver class.

        Validates that the re-exports point at the real drivers instead
        of shadowing aliases.
        """
        self.assertIs(hashers_package.Argon2Hasher, Argon2Hasher)
        self.assertIs(hashers_package.BcryptHasher, BcryptHasher)
