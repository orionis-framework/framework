import inspect
from orionis.console import reactor_provider as provider_module
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.core.reactor import Reactor
from orionis.console.reactor_provider import ReactorProvider
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.support.facades.reactor import Reactor as ReactorFacade
from orionis.test import TestCase

# Alias shared by the container binding and the facade accessor.
_REACTOR_ALIAS = "x-orionis-IReactor"


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
        self.singletons: list[tuple[object, object, str | None]] = []

    def singleton(
        self,
        abstract: object,
        concrete: object,
        alias: str | None = None,
    ) -> None:
        """
        Record a singleton binding.

        Parameters
        ----------
        abstract : object
            Contract used as the binding key.
        concrete : object
            Implementation bound to the contract.
        alias : str or None, optional
            Alternative key the binding is also reachable through.

        Returns
        -------
        None
        """
        self.singletons.append((abstract, concrete, alias))


class _StubReactorFacade:
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


class TestReactorProviderDefinition(TestCase):

    def testInheritsTheServiceProviderBase(self) -> None:
        """
        Extend the base ServiceProvider class.

        Validates the provider class hierarchy.
        """
        self.assertTrue(issubclass(ReactorProvider, ServiceProvider))

    def testIsNotDeferred(self) -> None:
        """
        Stay out of the deferred provider mechanism.

        Validates that the reactor is available as soon as the application
        boots, which is what the CLI entry point expects.
        """
        self.assertFalse(issubclass(ReactorProvider, DeferrableProvider))

    def testIsRegisteredAsACoreProvider(self) -> None:
        """
        Ship with the core providers booted by the framework.

        Validates that IReactor is bound without the application having to
        register anything by hand.
        """
        self.assertIn(ReactorProvider, CORE_PROVIDERS)

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the container passed to the constructor.

        Validates the container the provider binds services into.
        """
        app = _StubApp()
        self.assertIs(ReactorProvider(app).app, app)  # type: ignore[arg-type]

    def testBootIsDeclaredAsynchronous(self) -> None:
        """
        Declare the boot phase as an asynchronous method.

        Validates that boot can await the facade pinning.
        """
        self.assertTrue(inspect.iscoroutinefunction(ReactorProvider.boot))


class TestReactorProviderRegister(TestCase):

    def testBindsTheReactorContractAsASingleton(self) -> None:
        """
        Bind IReactor to the concrete Reactor implementation.

        Validates the single binding declared by the provider, including
        the alias used to reach it.
        """
        app = _StubApp()

        ReactorProvider(app).register()  # type: ignore[arg-type]

        self.assertEqual(app.singletons, [(IReactor, Reactor, _REACTOR_ALIAS)])

    def testRegisteredAliasMatchesTheFacadeAccessor(self) -> None:
        """
        Register the alias the Reactor facade resolves.

        Validates that the facade and the binding cannot drift apart.
        """
        self.assertEqual(ReactorFacade.getFacadeAccessor(), _REACTOR_ALIAS)


class TestReactorProviderBoot(TestCase):

    def setUp(self) -> None:
        """
        Replace the Reactor facade with a double before each test.

        Prevents the boot phase from pinning the real facade, which would
        require a fully booted application.
        """
        self._original_facade = provider_module.ReactorFacade
        self._facade = _StubReactorFacade()
        provider_module.ReactorFacade = self._facade
        self._app = _StubApp()

    def tearDown(self) -> None:
        """
        Restore the original Reactor facade after each test.

        Guarantees that module level state never leaks between tests.
        """
        provider_module.ReactorFacade = self._original_facade

    async def testBootPinsTheReactorFacade(self) -> None:
        """
        Pin the Reactor facade once the services are registered.

        Validates that facade access skips container resolution.
        """
        await ReactorProvider(self._app).boot()  # type: ignore[arg-type]

        self.assertEqual(self._facade.pinned, 1)

    async def testBootRegistersNoAdditionalBinding(self) -> None:
        """
        Keep the boot phase free of container registrations.

        Validates the separation between register() and boot().
        """
        await ReactorProvider(self._app).boot()  # type: ignore[arg-type]

        self.assertEqual(self._app.singletons, [])
