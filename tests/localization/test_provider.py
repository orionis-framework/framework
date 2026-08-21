import inspect
from orionis.container.providers.service_provider import ServiceProvider
from orionis.localization import provider as provider_module
from orionis.localization.contracts.manager import ILocalizationManager
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.manager import LocalizationManager
from orionis.localization.provider import LocalizationProvider
from orionis.test import TestCase

class _StubTranslator:
    """Translator double standing in for the shared instance."""

    __slots__ = ()

class _StubManager:
    """Localization manager double returning a fixed translator."""

    __slots__ = ("calls", "shared")

    def __init__(self, shared: object) -> None:
        self.shared = shared
        self.calls = 0

    def translator(self) -> object:
        """
        Return the configured translator double.

        Returns
        -------
        object
            Translator instance shared by the double.
        """
        self.calls += 1
        return self.shared

class _StubApp:
    """Container double recording bindings and resolutions."""

    __slots__ = ("bound", "manager", "resolved", "singletons")

    def __init__(self, manager: object | None = None) -> None:
        self.manager = manager
        self.singletons: list[tuple[object, object]] = []
        self.bound: list[tuple[object, object]] = []
        self.resolved: list[object] = []

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

    def instance(self, abstract: object, instance: object) -> None:
        """
        Record an already built instance binding.

        Parameters
        ----------
        abstract : object
            Contract used as the binding key.
        instance : object
            Instance bound to the contract.

        Returns
        -------
        None
        """
        self.bound.append((abstract, instance))

    async def make(self, abstract: object) -> object:
        """
        Resolve the stubbed manager for any requested contract.

        Parameters
        ----------
        abstract : object
            Contract requested by the provider.

        Returns
        -------
        object
            Manager double configured on the container.
        """
        self.resolved.append(abstract)
        return self.manager

class _StubLangFacade:
    """Language facade double counting how many times it was pinned."""

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

class TestLocalizationProviderDefinition(TestCase):
    """Validate the structural contract of the provider."""

    def testInheritsTheBaseServiceProvider(self) -> None:
        """
        Extend the base service provider.

        Validates that the provider participates in the standard
        register and boot lifecycle.
        """
        self.assertTrue(issubclass(LocalizationProvider, ServiceProvider))

    def testStoresTheApplicationReference(self) -> None:
        """
        Keep the container received by the constructor.

        Validates that both phases bind services into the very same
        container.
        """
        app = _StubApp()
        self.assertIs(LocalizationProvider(app).app, app)

    def testBootIsACoroutineFunction(self) -> None:
        """
        Declare the boot phase as asynchronous.

        Validates that boot can await container resolutions and facade
        pinning.
        """
        self.assertTrue(inspect.iscoroutinefunction(LocalizationProvider.boot))

class TestLocalizationProviderRegistration(TestCase):
    """Validate the bindings declared during registration."""

    def testRegistersTheManagerAsASingleton(self) -> None:
        """
        Bind the manager contract to its concrete implementation.

        Validates that a single manager serves the whole application.
        """
        app = _StubApp()
        LocalizationProvider(app).register()
        self.assertEqual(
            app.singletons,
            [(ILocalizationManager, LocalizationManager)],
        )

    def testRegistrationBindsNothingElse(self) -> None:
        """
        Avoid binding instances during registration.

        Validates that the translator is only built in the boot phase,
        once the configuration is available.
        """
        app = _StubApp()
        LocalizationProvider(app).register()
        self.assertEqual(app.bound, [])

class TestLocalizationProviderBoot(TestCase):
    """Validate the wiring performed during the boot phase."""

    def setUp(self) -> None:
        """
        Replace the language facade with a double.

        Prevents the boot phase from pinning the real facade, which
        would require a fully booted application.

        Returns
        -------
        None
        """
        self._original_facade = provider_module.LangFacade
        self._facade = _StubLangFacade()
        provider_module.LangFacade = self._facade
        self._translator = _StubTranslator()
        self._manager = _StubManager(self._translator)
        self._app = _StubApp(self._manager)

    def tearDown(self) -> None:
        """
        Restore the original language facade.

        Guarantees that module-level state is never leaked to other
        test cases.

        Returns
        -------
        None
        """
        provider_module.LangFacade = self._original_facade

    async def testBootResolvesTheManagerContract(self) -> None:
        """
        Resolve the manager contract exactly once.

        Validates that the provider depends on the contract instead of
        the concrete implementation.
        """
        await LocalizationProvider(self._app).boot()
        self.assertEqual(self._app.resolved, [ILocalizationManager])

    async def testBootBindsTheSharedTranslatorInstance(self) -> None:
        """
        Bind the translator built by the manager.

        Validates that consumers resolving the translator contract
        receive the very instance owned by the manager.
        """
        await LocalizationProvider(self._app).boot()
        self.assertEqual(self._app.bound, [(ITranslator, self._translator)])

    async def testBootBuildsTheTranslatorOnlyOnce(self) -> None:
        """
        Ask the manager for the translator a single time.

        Validates that booting never duplicates the translation cache.
        """
        await LocalizationProvider(self._app).boot()
        self.assertEqual(self._manager.calls, 1)

    async def testBootPinsTheLanguageFacade(self) -> None:
        """
        Pin the language facade after wiring the translator.

        Validates that template globals and controllers reach the
        translator without container resolution overhead.
        """
        await LocalizationProvider(self._app).boot()
        self.assertEqual(self._facade.pinned, 1)
