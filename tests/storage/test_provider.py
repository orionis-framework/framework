import inspect
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.storage import provider as provider_module
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.manager import StorageManager
from orionis.storage.provider import StorageProvider
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

class _StubStorageFacade:
    """Storage facade double counting how many times it was pinned."""

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

class TestStorageProviderDefinition(TestCase):

    def testInheritsTheFrameworkProviderBases(self) -> None:
        """
        Extend both ServiceProvider and DeferrableProvider.

        Validates the provider class hierarchy.
        """
        self.assertTrue(issubclass(StorageProvider, ServiceProvider))
        self.assertTrue(issubclass(StorageProvider, DeferrableProvider))

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the container passed to the constructor.

        Validates the container the provider binds services into.
        """
        app = _StubApp()
        self.assertIs(StorageProvider(app).app, app)

    def testProvidesExposesTheManagerContract(self) -> None:
        """
        Advertise IStorageManager as the deferred service.

        Validates the deferred-provider contract.
        """
        self.assertEqual(StorageProvider.provides(), [IStorageManager])

    def testBootIsDeclaredAsynchronous(self) -> None:
        """
        Declare the boot phase as an asynchronous method.

        Validates that boot can await the facade pinning.
        """
        self.assertTrue(inspect.iscoroutinefunction(StorageProvider.boot))

class TestStorageProviderRegister(TestCase):

    def testRegisterBindsExactlyOneService(self) -> None:
        """
        Bind a single service during registration.

        Validates that no extra binding leaks into the container.
        """
        app = _StubApp()
        StorageProvider(app).register()
        self.assertEqual(len(app.singletons), 1)

    def testRegisterBindsTheManagerAsSingleton(self) -> None:
        """
        Bind IStorageManager to the concrete StorageManager.

        Validates the contract resolved by the Storage facade.
        """
        app = _StubApp()
        StorageProvider(app).register()
        self.assertIn((IStorageManager, StorageManager), app.singletons)

class TestStorageProviderBoot(TestCase):

    def setUp(self) -> None:
        """
        Replace the storage facade with a double before each test.

        Prevents the boot phase from pinning the real facade, which
        would require a fully booted application.
        """
        self._original_facade = provider_module.StorageFacade
        self._facade = _StubStorageFacade()
        provider_module.StorageFacade = self._facade
        self._app = _StubApp()

    def tearDown(self) -> None:
        """
        Restore the original storage facade after each test.

        Guarantees that module-level state never leaks between tests.
        """
        provider_module.StorageFacade = self._original_facade

    async def testBootPinsTheStorageFacade(self) -> None:
        """
        Pin the storage facade once the services are registered.

        Validates that facade access skips container resolution.
        """
        await StorageProvider(self._app).boot()
        self.assertEqual(self._facade.pinned, 1)

    async def testBootRegistersNoAdditionalBinding(self) -> None:
        """
        Keep the boot phase free of container registrations.

        Validates the separation between register() and boot().
        """
        await StorageProvider(self._app).boot()
        self.assertEqual(self._app.singletons, [])
