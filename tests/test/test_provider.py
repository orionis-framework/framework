from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.test import TestCase
from orionis.test import provider as provider_module
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.core.engine import TestingEngine
from orionis.test.provider import TestingProvider

class _StubApp:
    """Application double recording every binding it receives."""

    __slots__ = ("singletons",)

    def __init__(self) -> None:
        self.singletons: list[tuple[object, object]] = []

    def singleton(self, abstract: object, concrete: object) -> None:
        """Record a singleton binding request."""
        self.singletons.append((abstract, concrete))

class _StubFacade:
    """Testing facade double counting how many times it was pinned."""

    __slots__ = ("pinned",)

    def __init__(self) -> None:
        self.pinned: int = 0

    async def pin(self) -> None:
        """Count a pin invocation."""
        self.pinned += 1

class TestTestingProviderDefinition(TestCase):

    def testExtendsServiceProvider(self) -> None:
        """
        Extend the base service provider.

        Validates that the provider participates in the standard
        register and boot lifecycle.
        """
        self.assertTrue(issubclass(TestingProvider, ServiceProvider))

    def testIsDeferrable(self) -> None:
        """
        Declare the provider as deferrable.

        Validates that the testing engine is only built when it is
        actually requested.
        """
        self.assertTrue(issubclass(TestingProvider, DeferrableProvider))

    def testPublishesTheEngineContract(self) -> None:
        """
        Publish the testing engine contract as the deferred service.

        Validates the key the container uses to trigger the deferred
        registration.
        """
        self.assertEqual(TestingProvider.provides(), [ITestingEngine])

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the application instance received at construction time.

        Validates that bindings are performed against the container that
        created the provider.
        """
        app = _StubApp()
        self.assertIs(TestingProvider(app).app, app)  # type: ignore[arg-type]

class TestTestingProviderRegistration(TestCase):

    def testRegisterBindsTheEngineAsSingleton(self) -> None:
        """
        Bind the concrete engine to its contract as a singleton.

        Validates that every consumer shares the same configured
        engine.
        """
        app = _StubApp()
        TestingProvider(app).register()  # type: ignore[arg-type]
        self.assertEqual(app.singletons, [(ITestingEngine, TestingEngine)])

    def testRegisterIsIdempotent(self) -> None:
        """
        Repeat the same binding when registration runs twice.

        Validates that a deferred provider re-registered by the
        container never changes the published binding.
        """
        app = _StubApp()
        provider = TestingProvider(app)  # type: ignore[arg-type]
        provider.register()
        provider.register()
        self.assertEqual(
            app.singletons,
            [(ITestingEngine, TestingEngine)] * 2,
        )

class TestTestingProviderBoot(TestCase):

    def setUp(self) -> None:
        """
        Replace the testing facade with a double before each scenario.

        Prevents the boot phase from pinning the real facade, which
        would require a fully booted application.
        """
        self._original_facade = provider_module.TestFacade
        self._facade = _StubFacade()
        provider_module.TestFacade = self._facade

    def tearDown(self) -> None:
        """
        Restore the original testing facade after each scenario.

        Guarantees that module level state is never leaked to the tests
        executed afterwards.
        """
        provider_module.TestFacade = self._original_facade

    async def testBootPinsTheFacade(self) -> None:
        """
        Pin the testing facade once the container is booted.

        Validates that the facade resolves the engine directly instead
        of deferring every attribute access.
        """
        await TestingProvider(_StubApp()).boot()  # type: ignore[arg-type]
        self.assertEqual(self._facade.pinned, 1)

    async def testBootPerformsNoBinding(self) -> None:
        """
        Leave the container untouched during the boot phase.

        Validates that bindings belong exclusively to the registration
        phase.
        """
        app = _StubApp()
        await TestingProvider(app).boot()  # type: ignore[arg-type]
        self.assertEqual(app.singletons, [])
