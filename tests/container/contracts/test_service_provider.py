# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
import inspect
from abc import ABC
from orionis.container.contracts.service_provider import IServiceProvider
from orionis.test import TestCase


class _ConcreteProvider(IServiceProvider):
    """Minimal IServiceProvider implementation for structural tests."""

    def register(self) -> None:
        """Skip registration; the stub binds nothing.

        Returns
        -------
        None
            No return value.
        """

    async def boot(self) -> None:
        """Skip booting; the stub initialises nothing.

        Returns
        -------
        None
            No return value.
        """


class TestIServiceProvider(TestCase):
    def testContractIsAnAbstractBaseClass(self) -> None:
        """
        Declare IServiceProvider as an ABC that cannot be instantiated.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(IServiceProvider, ABC))
        with self.assertRaises(TypeError):
            IServiceProvider()  # type: ignore[abstract]

    def testContractDeclaresExactlyTheExpectedAbstractMethods(self) -> None:
        """
        Declare exactly the register() and boot() lifecycle hooks.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(
            IServiceProvider.__abstractmethods__,
            frozenset({"register", "boot"}),
        )

    def testBootIsDeclaredAsynchronousAndRegisterIsNot(self) -> None:
        """
        Split the lifecycle into a sync register() and an async boot().

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(
            inspect.iscoroutinefunction(IServiceProvider.boot),
        )
        self.assertFalse(
            inspect.iscoroutinefunction(IServiceProvider.register),
        )

    async def testConcreteSubclassRunsBothLifecycleHooks(self) -> None:
        """
        Instantiate a concrete subclass and run both lifecycle hooks.

        Returns
        -------
        None
            No return value.
        """
        provider = _ConcreteProvider()
        self.assertIsInstance(provider, IServiceProvider)
        self.assertIsNone(provider.register())
        self.assertIsNone(await provider.boot())
