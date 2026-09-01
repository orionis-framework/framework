import inspect
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
        self.singletons: list[tuple[object, object]] = []

    def singleton(self, abstract: object, concrete: object) -> None:
        """
        Record a singleton binding.

        Parameters
        ----------
        abstract : object
            Contract used as the binding key.
        concrete : object
            Implementation bound to the contract.

        Returns
        -------
        None
        """
        self.singletons.append((abstract, concrete))


class _StubCryptFacade:
    """Facade double counting how many times it was pinned."""

    __slots__ = ("pinned",)

    def __init__(self) -> None:
        self.pinned = 0

    async def pin(self) -> None:
        """
        Count a pin invocation.

        Returns
        -------
        None
        """
        self.pinned += 1


class TestEncrypterProviderDefinition(TestCase):

    def testInheritsTheServiceProviderBase(self) -> None:
        """
        Extend the base ServiceProvider class.

        Validates the provider class hierarchy.
        """
        self.assertTrue(issubclass(EncrypterProvider, ServiceProvider))

    def testIsNotDeferred(self) -> None:
        """
        Stay out of the deferred provider mechanism.

        Validates the requirement imposed by the synchronous API: a deferred
        provider would leave the Crypt facade unpinned, so the first call of
        a synchronous consumer would receive a dispatcher instead of a value.
        """
        self.assertFalse(issubclass(EncrypterProvider, DeferrableProvider))

    def testIsRegisteredAsACoreProvider(self) -> None:
        """
        Ship with the core providers booted by the framework.

        Validates that IEncrypter is bound without the application having to
        register anything by hand.
        """
        self.assertIn(EncrypterProvider, CORE_PROVIDERS)

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the container passed to the constructor.

        Validates the container the provider binds services into.
        """
        app = _StubApp()
        self.assertIs(EncrypterProvider(app).app, app)

    def testBootIsDeclaredAsynchronous(self) -> None:
        """
        Declare the boot phase as an asynchronous method.

        Validates that boot can await the facade pinning.
        """
        self.assertTrue(inspect.iscoroutinefunction(EncrypterProvider.boot))


class TestEncrypterProviderRegister(TestCase):

    def testRegisterBindsTheEncrypterAsASingleton(self) -> None:
        """
        Bind IEncrypter to the concrete Encrypter implementation.

        Validates the contract resolved by the Crypt facade.
        """
        app = _StubApp()
        EncrypterProvider(app).register()
        self.assertEqual(app.singletons, [(IEncrypter, Encrypter)])


class TestEncrypterProviderBoot(TestCase):

    def setUp(self) -> None:
        """
        Replace the Crypt facade with a double before each test.

        Prevents the boot phase from pinning the real facade, which would
        require a fully booted application.
        """
        self._original_facade = provider_module.CryptFacade
        self._facade = _StubCryptFacade()
        provider_module.CryptFacade = self._facade
        self._app = _StubApp()

    def tearDown(self) -> None:
        """
        Restore the original Crypt facade after each test.

        Guarantees that module-level state never leaks between tests.
        """
        provider_module.CryptFacade = self._original_facade

    async def testBootPinsTheCryptFacade(self) -> None:
        """
        Pin the Crypt facade once the services are registered.

        Validates that facade access skips container resolution.
        """
        await EncrypterProvider(self._app).boot()
        self.assertEqual(self._facade.pinned, 1)

    async def testBootRegistersNoAdditionalBinding(self) -> None:
        """
        Keep the boot phase free of container registrations.

        Validates the separation between register() and boot().
        """
        await EncrypterProvider(self._app).boot()
        self.assertEqual(self._app.singletons, [])
