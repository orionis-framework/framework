import inspect
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.hashing import provider as provider_module
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.hash_manager import HashManager
from orionis.hashing.provider import HashProvider
from orionis.support.facades.hash import Hash
from orionis.test import TestCase

# Cheap cost parameters keeping the facade round trip fast.
_CHEAP_COSTS: dict[str, int] = {"rounds": 1, "memory": 8, "threads": 1}


class _StubApp:
    """Application double capturing every binding it receives."""

    __slots__ = ("singletons",)

    def __init__(self) -> None:
        """
        Initialise the list of recorded bindings.

        Returns
        -------
        None
        """
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


class _StubHashFacade:
    """Facade double counting how many times it was pinned."""

    __slots__ = ("pinned",)

    def __init__(self) -> None:
        """
        Initialise the pin counter.

        Returns
        -------
        None
        """
        self.pinned = 0

    async def pin(self) -> None:
        """
        Count a pin invocation.

        Returns
        -------
        None
        """
        self.pinned += 1


class TestHashProviderDefinition(TestCase):

    def testInheritsTheServiceProviderBase(self) -> None:
        """
        Extend the base ServiceProvider class.

        Validates the provider class hierarchy.
        """
        self.assertTrue(issubclass(HashProvider, ServiceProvider))

    def testIsNotDeferred(self) -> None:
        """
        Stay out of the deferred provider mechanism.

        Validates the requirement imposed by the synchronous API: a
        deferred provider would leave the Hash facade unpinned, so the
        first call of a synchronous consumer would receive a dispatcher
        instead of a value.
        """
        self.assertFalse(issubclass(HashProvider, DeferrableProvider))

    def testIsRegisteredAsACoreProvider(self) -> None:
        """
        Ship with the core providers booted by the framework.

        Validates that IHashManager is bound without the application
        having to register anything by hand.
        """
        self.assertIn(HashProvider, CORE_PROVIDERS)

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the container passed to the constructor.

        Validates the container the provider binds services into.
        """
        app = _StubApp()
        self.assertIs(HashProvider(app).app, app)  # type: ignore[arg-type]

    def testBootIsDeclaredAsynchronous(self) -> None:
        """
        Declare the boot phase as an asynchronous method.

        Validates that boot can await the facade pinning.
        """
        self.assertTrue(inspect.iscoroutinefunction(HashProvider.boot))


class TestHashProviderRegister(TestCase):

    def testRegisterBindsTheManagerAsASingleton(self) -> None:
        """
        Bind IHashManager to the concrete HashManager implementation.

        Validates the contract resolved by the Hash facade.
        """
        app = _StubApp()
        HashProvider(app).register()  # type: ignore[arg-type]
        self.assertEqual(app.singletons, [(IHashManager, HashManager)])


class TestHashProviderBoot(TestCase):

    def setUp(self) -> None:
        """
        Replace the Hash facade with a double before each test.

        Prevents the boot phase from pinning the real facade, which would
        require a fully booted application.
        """
        self._original_facade = provider_module.HashFacade
        self._facade = _StubHashFacade()
        provider_module.HashFacade = self._facade
        self._app = _StubApp()

    def tearDown(self) -> None:
        """
        Restore the original Hash facade after each test.

        Guarantees that module level state never leaks between tests.
        """
        provider_module.HashFacade = self._original_facade

    async def testBootPinsTheHashFacade(self) -> None:
        """
        Pin the Hash facade once the services are registered.

        Validates that facade access skips container resolution.
        """
        await HashProvider(self._app).boot()  # type: ignore[arg-type]
        self.assertEqual(self._facade.pinned, 1)

    async def testBootRegistersNoAdditionalBinding(self) -> None:
        """
        Keep the boot phase free of container registrations.

        Validates the separation between register() and boot().
        """
        await HashProvider(self._app).boot()  # type: ignore[arg-type]
        self.assertEqual(self._app.singletons, [])


class TestHashFacade(TestCase):

    def testAccessorIsTheManagerContract(self) -> None:
        """
        Resolve the hashing manager contract from the container.

        Validates the accessor the facade metaclass relies on.
        """
        self.assertIs(Hash.getFacadeAccessor(), IHashManager)

    async def testResolvesTheRegisteredManager(self) -> None:
        """
        Resolve the manager bound by the provider.

        Validates that the booted application exposes the service.
        """
        self.assertIsInstance(await Hash.resolve(), HashManager)

    def testIsPinnedAfterTheApplicationBoots(self) -> None:
        """
        Expose a pinned instance once the application has booted.

        Validates the wiring that keeps the facade synchronous.
        """
        self.assertIsInstance(Hash._pinned_instance, HashManager)

    def testHashesAndVerifiesWithoutAwaiting(self) -> None:
        """
        Hash and verify a value through the pinned facade.

        Validates the synchronous API application code depends on.
        """
        hashed = Hash.make("my-secret-password", **_CHEAP_COSTS)
        self.assertIsInstance(hashed, str)
        self.assertTrue(Hash.check("my-secret-password", hashed))
        self.assertFalse(Hash.check("other-password", hashed))
