from __future__ import annotations
import inspect
from abc import ABC
from orionis.test import TestCase
from orionis.container.contracts.facade import IFacade
from orionis.container.facades.facade import Facade

_ABSTRACT_METHODS = frozenset({
    "getFacadeAccessor", "resolve", "pin", "unpin",
})

class _StubFacade(IFacade):
    """Minimal IFacade implementation used only for structural tests."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """Return a fixed accessor key."""
        return "stub"

    @classmethod
    async def resolve(cls, *_args: object, **_kwargs: object) -> object:
        """Return nothing, standing in for a real container lookup."""
        return None

    @classmethod
    async def pin(cls) -> None:
        """Skip pinning; the stub keeps no state."""

    @classmethod
    def unpin(cls) -> None:
        """Skip unpinning; the stub keeps no state."""

class TestIFacade(TestCase):

    def testContractIsAnAbstractBaseClass(self) -> None:
        """
        Declare IFacade as an ABC that cannot be instantiated directly.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(issubclass(IFacade, ABC))
        with self.assertRaises(TypeError):
            IFacade()  # type: ignore[abstract]

    def testContractDeclaresExactlyTheExpectedAbstractMethods(self) -> None:
        """
        Declare exactly the documented set of abstract methods.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(IFacade.__abstractmethods__, _ABSTRACT_METHODS)

    def testConcreteSubclassCanBeInstantiated(self) -> None:
        """
        Instantiate a subclass that implements every abstract method.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_StubFacade(), IFacade)

    def testFacadeImplementationMatchesTheContractSignatures(self) -> None:
        """
        Keep the Facade parameter names aligned with the contract.

        Returns
        -------
        None
            This method does not return a value.
        """
        for name in sorted(_ABSTRACT_METHODS):
            expected = list(
                inspect.signature(getattr(IFacade, name)).parameters,
            )
            actual = list(
                inspect.signature(getattr(Facade, name)).parameters,
            )
            self.assertEqual(actual, expected, f"signature drift on {name!r}")
