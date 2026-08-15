from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.hash_manager import HashManager
from orionis.hashing.provider import HashProvider
from orionis.support.facades.hash import Hash
from orionis.test import TestCase

class _FakeApp:
    """Minimal application stub recording singleton bindings."""

    def __init__(self) -> None:
        """Initialise the list of recorded bindings."""
        self.singletons: list[tuple[object, object]] = []

    def singleton(self, abstract: object, concrete: object) -> None:
        """
        Record a singleton binding.

        Parameters
        ----------
        abstract : object
            Contract used as the container key.
        concrete : object
            Implementation bound to the contract.
        """
        self.singletons.append((abstract, concrete))

class TestHashProvider(TestCase):
    """Tests for the hashing service provider."""

    def testInheritsServiceProvider(self) -> None:
        """
        Verify HashProvider inherits from ServiceProvider.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(issubclass(HashProvider, ServiceProvider))

    def testIsRegisteredAsCoreProvider(self) -> None:
        """
        Verify the provider is booted with the framework core providers.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIn(HashProvider, CORE_PROVIDERS)

    def testRegisterBindsManagerAsSingleton(self) -> None:
        """
        Verify IHashManager is bound to HashManager as a singleton.

        Returns
        -------
        None
            This method does not return a value.
        """
        app = _FakeApp()
        HashProvider(app).register()  # type: ignore[arg-type]
        self.assertEqual(app.singletons, [(IHashManager, HashManager)])

class TestHashFacade(TestCase):
    """Tests for the Hash facade wiring."""

    def testFacadeAccessorIsManagerContract(self) -> None:
        """
        Verify the facade resolves the hashing manager contract.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIs(Hash.getFacadeAccessor(), IHashManager)

    async def testFacadeIsPinnedAfterBoot(self) -> None:
        """
        Verify the booted application pins the facade to a manager.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(await Hash.resolve(), HashManager)
        self.assertIsInstance(Hash._pinned_instance, HashManager)

    def testPinnedFacadeIsUsedSynchronously(self) -> None:
        """
        Verify the pinned facade hashes without awaiting the call.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = Hash.make("my-secret-password")
        self.assertIsInstance(hashed, str)
        self.assertTrue(Hash.check("my-secret-password", hashed))
        self.assertFalse(Hash.check("other-password", hashed))

    async def testFacadeHashesAndVerifies(self) -> None:
        """
        Verify the facade exposes the full hashing round trip.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = await Hash.resolve()
        hashed = manager.make("my-secret-password")
        self.assertTrue(manager.check("my-secret-password", hashed))
        self.assertFalse(manager.check("other-password", hashed))
