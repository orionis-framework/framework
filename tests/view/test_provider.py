import inspect
from orionis.container.providers.service_provider import ServiceProvider
from orionis.test import TestCase
from orionis.view import provider as provider_module
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.environment import IViewEnvironment
from orionis.view.contracts.factory import IViewFactory
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from orionis.view.extensions import CsrfExtension
from orionis.view.factory import ViewFactory
from orionis.view.provider import ViewServiceProvider

# Full contract of template globals published by the provider.
_EXPECTED_GLOBALS: frozenset[str] = frozenset({
    "__",
    "app",
    "asset",
    "cache",
    "choice",
    "collect",
    "config",
    "csrf_field",
    "csrf_token",
    "decrypt",
    "dump",
    "encrypt",
    "errors",
    "flash",
    "framework_version",
    "locale",
    "locales",
    "now",
    "old",
    "python_version",
    "request",
    "route",
    "secure_asset",
    "secure_url",
    "session",
    "stringable",
    "today",
    "trans",
    "url",
})

# Full contract of template filters published by the provider.
_EXPECTED_FILTERS: frozenset[str] = frozenset({"json", "markdown"})

class _StubEnvironment:
    """View environment double recording every registration it receives."""

    __slots__ = ("extensions", "filters", "globals")

    def __init__(self) -> None:
        self.globals: dict[str, object] = {}
        self.filters: dict[str, object] = {}
        self.extensions: list[object] = []

    def addGlobal(self, name: str, value: object) -> None:
        """Record a template global."""
        self.globals[name] = value

    def addFilter(self, name: str, callback: object) -> None:
        """Record a template filter."""
        self.filters[name] = callback

    def addExtension(self, extension: object) -> None:
        """Record a Jinja2 extension."""
        self.extensions.append(extension)

class _StubApp:
    """Application double capturing bindings and resolving the environment."""

    __slots__ = ("environment", "resolved", "singletons")

    def __init__(self, environment: _StubEnvironment | None = None) -> None:
        self.environment: _StubEnvironment | None = environment
        self.singletons: list[tuple[object, object]] = []
        self.resolved: list[object] = []

    def singleton(self, abstract: object, concrete: object) -> None:
        """Record a singleton binding."""
        self.singletons.append((abstract, concrete))

    def config(self, _key: str) -> object:
        """Return no configured value so builders use their defaults."""
        return None

    async def make(self, abstract: object) -> object:
        """Return the stubbed environment for any requested abstract."""
        self.resolved.append(abstract)
        return self.environment

class _StubViewFacade:
    """View facade double counting how many times it was pinned."""

    __slots__ = ("pinned",)

    def __init__(self) -> None:
        self.pinned: int = 0

    async def pin(self) -> None:
        """Count a pin invocation."""
        self.pinned += 1

class TestViewServiceProviderDefinition(TestCase):

    def testInheritsServiceProvider(self) -> None:
        """
        Verify ViewServiceProvider extends the base service provider.

        Validates that the provider participates in the standard
        register/boot lifecycle of the container.
        """
        self.assertTrue(issubclass(ViewServiceProvider, ServiceProvider))

    def testStoresApplicationReference(self) -> None:
        """
        Store the application container passed to the constructor.

        Validates that the provider keeps the container it must bind
        services into.
        """
        app = _StubApp()
        self.assertIs(ViewServiceProvider(app).app, app)

    def testBootIsCoroutineFunction(self) -> None:
        """
        Verify boot is declared as an asynchronous method.

        Validates that the boot phase can await container resolutions
        and facade pinning.
        """
        self.assertTrue(
            inspect.iscoroutinefunction(ViewServiceProvider.boot),
        )

class TestViewServiceProviderRegister(TestCase):

    def testRegisterBindsThreeSingletons(self) -> None:
        """
        Bind exactly three view services during registration.

        Validates that no extra binding leaks into the container.
        """
        app = _StubApp()
        ViewServiceProvider(app).register()
        self.assertEqual(len(app.singletons), 3)

    def testRegisterBindsEnvironmentContract(self) -> None:
        """
        Bind IViewEnvironment to the concrete ViewEnvironment.

        Validates that the sole owner of the Jinja2 environment is
        resolvable through its contract.
        """
        app = _StubApp()
        ViewServiceProvider(app).register()
        self.assertIn((IViewEnvironment, ViewEnvironment), app.singletons)

    def testRegisterBindsEngineContract(self) -> None:
        """
        Bind IViewEngine to the concrete Jinja2Engine.

        Validates that the rendering engine is resolvable through its
        contract.
        """
        app = _StubApp()
        ViewServiceProvider(app).register()
        self.assertIn((IViewEngine, Jinja2Engine), app.singletons)

    def testRegisterBindsFactoryContract(self) -> None:
        """
        Bind IViewFactory to the concrete ViewFactory.

        Validates that the public entry-point used by controllers is
        resolvable through its contract.
        """
        app = _StubApp()
        ViewServiceProvider(app).register()
        self.assertIn((IViewFactory, ViewFactory), app.singletons)

    def testRegisterBindsEnvironmentBeforeEngine(self) -> None:
        """
        Bind the environment before the engine that consumes it.

        Validates the registration order required for the engine to
        resolve its dependency.
        """
        app = _StubApp()
        ViewServiceProvider(app).register()
        abstracts = [abstract for abstract, _ in app.singletons]
        self.assertLess(
            abstracts.index(IViewEnvironment),
            abstracts.index(IViewEngine),
        )

class TestViewServiceProviderBoot(TestCase):

    def setUp(self) -> None:
        """
        Replace the view facade with a double before each test.

        Prevents the boot phase from pinning the real facade, which
        would require a fully booted application.
        """
        self._original_facade = provider_module.ViewFacade
        self._facade = _StubViewFacade()
        provider_module.ViewFacade = self._facade
        self._environment = _StubEnvironment()
        self._app = _StubApp(self._environment)

    def tearDown(self) -> None:
        """
        Restore the original view facade after each test.

        Guarantees that module-level state is never leaked to other
        test cases.
        """
        provider_module.ViewFacade = self._original_facade

    async def _boot(self) -> None:
        """Run the boot phase against the stubbed application."""
        await ViewServiceProvider(self._app).boot()

    async def testBootResolvesEnvironmentSingleton(self) -> None:
        """
        Resolve the environment contract exactly once during boot.

        Validates that every registration targets the same shared
        environment instance.
        """
        await self._boot()
        self.assertEqual(self._app.resolved, [IViewEnvironment])

    async def testBootRegistersEveryTemplateGlobal(self) -> None:
        """
        Register the complete catalogue of template globals.

        Validates the public contract of names available inside every
        rendered template.
        """
        await self._boot()
        self.assertEqual(set(self._environment.globals), _EXPECTED_GLOBALS)

    async def testBootAliasesTranslationGlobal(self) -> None:
        """
        Expose the translation global under both trans and __.

        Validates that the conventional alias points at the very same
        callable rather than a second closure.
        """
        await self._boot()
        globals_ = self._environment.globals
        self.assertIs(globals_["__"], globals_["trans"])

    async def testBootRegistersCallableGlobals(self) -> None:
        """
        Register callable or object-based globals only.

        Validates that no builder leaks a plain None into the template
        namespace.
        """
        await self._boot()
        self.assertTrue(
            all(value is not None for value in self._environment.globals.values()),
        )

    async def testBootRegistersEveryTemplateFilter(self) -> None:
        """
        Register the complete catalogue of template filters.

        Validates the public contract of filters usable with the pipe
        operator inside templates.
        """
        await self._boot()
        self.assertEqual(set(self._environment.filters), _EXPECTED_FILTERS)

    async def testBootRegistersFiltersAsCallables(self) -> None:
        """
        Register every filter as a callable object.

        Validates that Jinja2 receives usable filter implementations.
        """
        await self._boot()
        self.assertTrue(
            all(callable(value) for value in self._environment.filters.values()),
        )

    async def testBootRegistersCsrfExtension(self) -> None:
        """
        Register the CSRF extension with the environment.

        Validates that the ``{% csrf %}`` tag is available in templates
        after boot.
        """
        await self._boot()
        self.assertEqual(self._environment.extensions, [CsrfExtension])

    async def testBootPinsViewFacade(self) -> None:
        """
        Pin the view facade once the environment is fully configured.

        Validates that controllers get zero-resolution access to the
        view factory on the hot path.
        """
        await self._boot()
        self.assertEqual(self._facade.pinned, 1)
