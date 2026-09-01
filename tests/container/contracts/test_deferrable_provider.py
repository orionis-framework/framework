from __future__ import annotations
from abc import ABC
from orionis.test import TestCase
from orionis.container.contracts.deferrable_provider import IDeferrableProvider

class _ConcreteProvider(IDeferrableProvider):
    """Minimal IDeferrableProvider implementation for structural tests."""

    @classmethod
    def provides(cls) -> list[type | str]:
        """Return the services published by this provider."""
        return [int, "x-orionis-probe"]

class TestIDeferrableProvider(TestCase):

    def testContractIsAnAbstractBaseClass(self) -> None:
        """
        Declare IDeferrableProvider as an ABC that cannot be instantiated.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(issubclass(IDeferrableProvider, ABC))
        with self.assertRaises(TypeError):
            IDeferrableProvider()  # type: ignore[abstract]

    def testContractDeclaresExactlyTheProvidesMethod(self) -> None:
        """
        Declare provides() as the single abstract member of the contract.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(
            IDeferrableProvider.__abstractmethods__,
            frozenset({"provides"}),
        )

    def testConcreteSubclassPublishesItsDeclaredServices(self) -> None:
        """
        Instantiate a concrete subclass and read back its published services.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_ConcreteProvider(), IDeferrableProvider)
        self.assertEqual(
            _ConcreteProvider.provides(),
            [int, "x-orionis-probe"],
        )
