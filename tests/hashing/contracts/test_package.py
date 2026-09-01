from orionis.hashing import contracts as contracts_package
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.contracts.hasher import IHasher
from orionis.test import TestCase


class TestHashingContractsPackage(TestCase):

    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """
        Declare exactly the two hashing contracts as public exports.

        Validates that consumers can import both interfaces from the
        package root.
        """
        self.assertEqual(
            contracts_package.__all__,
            ["IHashManager", "IHasher"],
        )

    def testReExportsBothContracts(self) -> None:
        """
        Bind every exported name to its contract class.

        Validates that the re-exports point at the real interfaces
        instead of shadowing aliases.
        """
        self.assertIs(contracts_package.IHashManager, IHashManager)
        self.assertIs(contracts_package.IHasher, IHasher)
