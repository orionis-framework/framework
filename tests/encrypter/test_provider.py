# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify encrypter service registration and synchronous facade preparation."""

import inspect
from unittest.mock import patch
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.encrypter import provider as provider_module
from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.encrypter.encrypter import Encrypter
from orionis.encrypter.provider import EncrypterProvider
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.test import TestCase


class _StubApp:
    """Application double capturing every binding it receives."""

    __slots__ = ("singletons",)

    def __init__(self) -> None:
        """Initialize the stub with its configured state.

        Returns
        -------
        None
            No return value.
        """
        self.singletons: list[tuple[object, object]] = []

    def singleton(self, abstract: object, concrete: object) -> None:
        """Record a singleton binding.

        Parameters
        ----------
        abstract : object
            Contract used as the binding key.
        concrete : object
            Implementation bound to the contract.

        Returns
        -------
        None
            No return value.
        """
        self.singletons.append((abstract, concrete))


class _StubCryptFacade:
    """Facade double counting how many times it was pinned."""

    __slots__ = ("pinned",)

    def __init__(self) -> None:
        """Initialize the stub with its configured state.

        Returns
        -------
        None
            No return value.
        """
        self.pinned = 0

    async def pin(self) -> None:
        """Count a pin invocation.

        Returns
        -------
        None
            No return value.
        """
        self.pinned += 1


class TestEncrypterProviderDefinition(TestCase):
    """Check the eager provider's registration and lifecycle contract."""

    def testInheritsTheServiceProviderBase(self) -> None:
        """Extend the base ServiceProvider class.

        Validates the provider class hierarchy.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(EncrypterProvider, ServiceProvider))

    def testIsNotDeferred(self) -> None:
        """Stay out of the deferred provider mechanism.

        Validates the requirement imposed by the synchronous API: a deferred
        provider would leave the Crypt facade unpinned, so the first call of
        a synchronous consumer would receive a dispatcher instead of a value.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(issubclass(EncrypterProvider, DeferrableProvider))

    def testIsRegisteredAsACoreProvider(self) -> None:
        """Ship with the core providers booted by the framework.

        Validates that IEncrypter is bound without the application having to
        register anything by hand.

        Returns
        -------
        None
            No return value.
        """
        self.assertIn(EncrypterProvider, CORE_PROVIDERS)

    def testStoresTheApplicationReference(self) -> None:
        """Keep the container passed to the constructor.

        Validates the container the provider binds services into.

        Returns
        -------
        None
            No return value.
        """
        app = _StubApp()
        self.assertIs(EncrypterProvider(app).app, app)

    def testBootIsDeclaredAsynchronous(self) -> None:
        """Declare the boot phase as an asynchronous method.

        Validates that boot can await the facade pinning.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(inspect.iscoroutinefunction(EncrypterProvider.boot))


class TestEncrypterProviderRegister(TestCase):
    """Verify the binding installed during service registration."""

    def testRegisterBindsTheEncrypterAsASingleton(self) -> None:
        """Bind IEncrypter to the concrete Encrypter implementation.

        Validates the contract resolved by the Crypt facade.

        Returns
        -------
        None
            No return value.
        """
        app = _StubApp()
        EncrypterProvider(app).register()
        self.assertEqual(app.singletons, [(IEncrypter, Encrypter)])


class TestEncrypterProviderBoot(TestCase):
    """Verify facade pinning without changing global facade state."""

    def setUp(self) -> None:
        """Replace the Crypt facade with a double before each test.

        Prevents the boot phase from pinning the real facade, which would
        require a fully booted application.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        self._facade = _StubCryptFacade()
        self.enterContext(patch.object(provider_module, "CryptFacade", self._facade))
        self._app = _StubApp()

    async def testBootPinsTheCryptFacade(self) -> None:
        """Pin the Crypt facade once the services are registered.

        Validates that facade access skips container resolution.

        Returns
        -------
        None
            No return value.
        """
        await EncrypterProvider(self._app).boot()
        self.assertEqual(self._facade.pinned, 1)

    async def testBootRegistersNoAdditionalBinding(self) -> None:
        """Keep the boot phase free of container registrations.

        Validates the separation between register() and boot().

        Returns
        -------
        None
            No return value.
        """
        await EncrypterProvider(self._app).boot()
        self.assertEqual(self._app.singletons, [])
