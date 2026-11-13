# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
import inspect
from abc import ABC
from orionis.container.contracts.facade import IFacade
from orionis.container.facades.facade import Facade
from orionis.test import TestCase

_ABSTRACT_METHODS = frozenset(
    {
        "getFacadeAccessor",
        "resolve",
        "pin",
        "unpin",
    },
)


class _StubFacade(IFacade):
    """Minimal IFacade implementation used only for structural tests."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """Return a fixed accessor key.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub"

    @classmethod
    async def resolve(cls, *_args: object, **_kwargs: object) -> object:
        """Return nothing, standing in for a real container lookup.

        Parameters
        ----------
        *_args : object
            Arguments passed to the wrapped callable.
        **_kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return None

    @classmethod
    async def pin(cls) -> None:
        """Skip pinning; the stub keeps no state.

        Returns
        -------
        None
            No return value.
        """

    @classmethod
    def unpin(cls) -> None:
        """Skip unpinning; the stub keeps no state.

        Returns
        -------
        None
            No return value.
        """


class TestIFacade(TestCase):
    def testContractIsAnAbstractBaseClass(self) -> None:
        """
        Declare IFacade as an ABC that cannot be instantiated directly.

        Returns
        -------
        None
            No return value.
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
            No return value.
        """
        self.assertEqual(IFacade.__abstractmethods__, _ABSTRACT_METHODS)

    def testConcreteSubclassCanBeInstantiated(self) -> None:
        """
        Instantiate a subclass that implements every abstract method.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(_StubFacade(), IFacade)

    def testFacadeImplementationMatchesTheContractSignatures(self) -> None:
        """Match runtime parameter kinds, defaults, annotations, and return types."""
        for name in sorted(_ABSTRACT_METHODS):
            with self.subTest(method=name):
                expected = inspect.signature(getattr(IFacade, name), eval_str=True)
                actual = inspect.signature(getattr(Facade, name), eval_str=True)
                self.assertEqual(
                    [item for key, item in actual.parameters.items() if key != "self"],
                    [
                        item
                        for key, item in expected.parameters.items()
                        if key != "self"
                    ],
                )
                self.assertEqual(actual.return_annotation, expected.return_annotation)
