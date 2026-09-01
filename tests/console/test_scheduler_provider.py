import inspect
from orionis.console import scheduler_provider as provider_module
from orionis.console.contracts.schedule import ISchedule
from orionis.console.contracts.store import IScheduleStore
from orionis.console.scheduler_provider import ScheduleProvider
from orionis.console.tasks.schedule import Schedule
from orionis.console.tasks.store import ScheduleStore
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.support.facades.schedule import Schedule as ScheduleFacade
from orionis.test import TestCase


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


class _StubScheduleFacade:
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


class TestScheduleProviderDefinition(TestCase):

    def testInheritsTheServiceProviderBase(self) -> None:
        """
        Extend the base ServiceProvider class.

        Validates the provider class hierarchy.
        """
        self.assertTrue(issubclass(ScheduleProvider, ServiceProvider))

    def testIsNotDeferred(self) -> None:
        """
        Stay out of the deferred provider mechanism.

        Validates that the schedule facade is pinned during the regular
        boot phase instead of on first resolution.
        """
        self.assertFalse(issubclass(ScheduleProvider, DeferrableProvider))

    def testIsRegisteredAsACoreProvider(self) -> None:
        """
        Ship with the core providers booted by the framework.

        Validates that ISchedule is bound without the application having to
        register anything by hand.
        """
        self.assertIn(ScheduleProvider, CORE_PROVIDERS)

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the container passed to the constructor.

        Validates the container the provider binds services into.
        """
        app = _StubApp()
        self.assertIs(ScheduleProvider(app).app, app)  # type: ignore[arg-type]

    def testBootIsDeclaredAsynchronous(self) -> None:
        """
        Declare the boot phase as an asynchronous method.

        Validates that boot can await the facade pinning.
        """
        self.assertTrue(inspect.iscoroutinefunction(ScheduleProvider.boot))


class TestScheduleProviderRegister(TestCase):

    def testBindsTheStoreBeforeTheScheduleContract(self) -> None:
        """
        Bind both contracts, the store first.

        Validates the order required by the container: Schedule declares
        IScheduleStore as a constructor dependency, and an interface can
        only be auto resolved once it owns an explicit binding.
        """
        app = _StubApp()

        ScheduleProvider(app).register()  # type: ignore[arg-type]

        self.assertEqual(
            app.singletons,
            [(IScheduleStore, ScheduleStore), (ISchedule, Schedule)],
        )

    def testFacadeAccessorIsTheScheduleContract(self) -> None:
        """
        Resolve the schedule contract from the container.

        Validates that the facade reads the very contract the provider
        registers.
        """
        self.assertIs(ScheduleFacade.getFacadeAccessor(), ISchedule)


class TestScheduleProviderBoot(TestCase):

    def setUp(self) -> None:
        """
        Replace the Schedule facade with a double before each test.

        Prevents the boot phase from pinning the real facade, which would
        require a fully booted application.
        """
        self._original_facade = provider_module.ScheduleFacade
        self._facade = _StubScheduleFacade()
        provider_module.ScheduleFacade = self._facade
        self._app = _StubApp()

    def tearDown(self) -> None:
        """
        Restore the original Schedule facade after each test.

        Guarantees that module level state never leaks between tests.
        """
        provider_module.ScheduleFacade = self._original_facade

    async def testBootPinsTheScheduleFacade(self) -> None:
        """
        Pin the Schedule facade once the services are registered.

        Validates that facade access skips container resolution.
        """
        await ScheduleProvider(self._app).boot()  # type: ignore[arg-type]

        self.assertEqual(self._facade.pinned, 1)

    async def testBootRegistersNoAdditionalBinding(self) -> None:
        """
        Keep the boot phase free of container registrations.

        Validates the separation between register() and boot().
        """
        await ScheduleProvider(self._app).boot()  # type: ignore[arg-type]

        self.assertEqual(self._app.singletons, [])
