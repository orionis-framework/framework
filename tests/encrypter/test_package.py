# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify the public encryption package exports."""

from orionis import encrypter as package
from orionis.encrypter.encrypter import Encrypter
from orionis.test import TestCase


class TestEncrypterPackage(TestCase):
    """Check the exported service name and implementation identity."""

    def testPublishesOnlyTheEncrypterClass(self) -> None:
        """Export a single public name from the package root.

        Validates the surface consumers may import from
        ``orionis.encrypter``.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(package.__all__, ["Encrypter"])

    def testExportedNameResolvesToTheImplementation(self) -> None:
        """Bind the exported name to the concrete implementation.

        Validates that the re-export points at the real class instead of
        a shadowing alias.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(package.Encrypter, Encrypter)
