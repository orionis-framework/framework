import inspect
from orionis.container.providers.service_provider import ServiceProvider
from orionis.logging import provider as provider_module
from orionis.logging.contracts.logger import ILogger
from orionis.logging.logger import Logger
from orionis.logging.provider import LoggerProvider
from orionis.test import TestCase

# Alias under which the logger contract is published in the container.
_LOGGER_ALIAS = "x-orionis-ILogger"

class _StubApp:
    """Container double recording every binding requested by the provider."""

    __slots__ = ("singletons",)

    def __init__(self) -> None:
        """Prepare the list collecting the recorded bindings."""
        self.singletons: list[tuple[object, object, str | None]] = []

    def singleton(
        self,
        abstract: object,
        concrete: object,
        alias: str | None = None,
    ) -> None:
        """Record a singleton binding request."""
        self.singletons.append((abstract, concrete, alias))

class _StubFacade:
    """Logger facade double counting how many times it was pinned."""

    __slots__ = ("pinned",)

    def __init__(self) -> None:
        """Start the pin counter at zero."""
        self.pinned: int = 0

    async def pin(self) -> None:
        """Count a pin invocation."""
        self.pinned += 1

class TestLoggerProviderDefinition(TestCase):

    def testInheritsFromServiceProvider(self) -> None:
        """
        Declare the provider as a standard service provider.

        Validates that it participates in the register and boot lifecycle
        driven by the application container.
        """
        self.assertTrue(issubclass(LoggerProvider, ServiceProvider))

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the container received by the constructor.

        Validates that the provider binds services into the very same
        container it was created with.
        """
        app = _StubApp()
        self.assertIs(LoggerProvider(app).app, app)

    def testBootIsAsynchronous(self) -> None:
        """
        Declare the boot phase as a coroutine function.

        Validates that the provider can await the facade pinning performed
        after every service is registered.
        """
        self.assertTrue(inspect.iscoroutinefunction(LoggerProvider.boot))

class TestLoggerProviderRegister(TestCase):

    def testRegisterBindsASingleService(self) -> None:
        """
        Bind exactly one service during registration.

        Validates that no additional binding leaks into the container.
        """
        app = _StubApp()
        LoggerProvider(app).register()
        self.assertEqual(len(app.singletons), 1)

    def testRegisterBindsTheContractToTheImplementation(self) -> None:
        """
        Bind the logger contract to the concrete implementation.

        Validates that resolving ILogger yields the framework logger under the
        internal alias used by the facade.
        """
        app = _StubApp()
        LoggerProvider(app).register()
        self.assertEqual(app.singletons[0], (ILogger, Logger, _LOGGER_ALIAS))

class TestLoggerProviderBoot(TestCase):

    def setUp(self) -> None:
        """Replace the logger facade with a double before each test."""
        self._original_facade = provider_module.LoggerFacade
        self._facade = _StubFacade()
        provider_module.LoggerFacade = self._facade
        self._app = _StubApp()

    def tearDown(self) -> None:
        """Restore the original logger facade after each test."""
        provider_module.LoggerFacade = self._original_facade

    async def testBootPinsTheLoggerFacade(self) -> None:
        """
        Pin the logger facade exactly once during boot.

        Validates that later facade accesses become direct passthroughs
        instead of deferred dispatchers.
        """
        await LoggerProvider(self._app).boot()
        self.assertEqual(self._facade.pinned, 1)

    async def testBootDoesNotRegisterAnyService(self) -> None:
        """
        Leave the container untouched during the boot phase.

        Validates that every binding happens in the registration phase, as
        required by the provider lifecycle.
        """
        await LoggerProvider(self._app).boot()
        self.assertEqual(self._app.singletons, [])
