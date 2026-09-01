from orionis import encrypter as package
from orionis.encrypter.encrypter import Encrypter
from orionis.test import TestCase


class TestEncrypterPackage(TestCase):

    def testPublishesOnlyTheEncrypterClass(self) -> None:
        """
        Export a single public name from the package root.

        Validates the surface consumers may import from
        ``orionis.encrypter``.
        """
        self.assertEqual(package.__all__, ["Encrypter"])

    def testExportedNameResolvesToTheImplementation(self) -> None:
        """
        Bind the exported name to the concrete implementation.

        Validates that the re-export points at the real class instead of
        a shadowing alias.
        """
        self.assertIs(package.Encrypter, Encrypter)
