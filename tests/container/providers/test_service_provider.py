from __future__ import annotations
import inspect
from orionis.test import TestCase
from orionis.container.contracts.service_provider import IServiceProvider
from orionis.container.providers.service_provider import ServiceProvider

# ---------------------------------------------------------------------------
# Module-level doubles — no external dependencies
# ---------------------------------------------------------------------------

class _FakeApp:
    """Lightweight application stub; satisfies the type hint without booting."""

class _FullProvider(ServiceProvider):
    """Subclass recording both register() and boot() invocations."""

    def __init__(self, app: _FakeApp) -> None:
        """Store the application and initialise the call recorders."""
        super().__init__(app)
        self.register_calls: int = 0
        self.boot_calls: int = 0

    def register(self) -> None:
        """Record a synchronous registration call."""
        self.register_calls += 1

    async def boot(self) -> None:
        """Record an asynchronous boot call."""
        self.boot_calls += 1

# ===========================================================================
# Construction and contract
# ===========================================================================

class TestServiceProviderConstruction(TestCase):

    def testApplicationIsStoredOnTheInstance(self) -> None:
        """
        Keep the injected application object untouched on the provider.

        Returns
        -------
        None
            This method does not return a value.
        """
        app = _FakeApp()
        self.assertIs(_FullProvider(app).app, app)

    def testProvidersKeepIndependentApplicationReferences(self) -> None:
        """
        Store independent application references on separate providers.

        Returns
        -------
        None
            This method does not return a value.
        """
        first, second = _FakeApp(), _FakeApp()
        self.assertIsNot(
            _FullProvider(first).app,
            _FullProvider(second).app,
        )

    def testProviderSatisfiesTheServiceProviderContract(self) -> None:
        """
        Satisfy the IServiceProvider contract with a concrete provider.

        Returns
        -------
        None
            This method does not return a value.
        """
        provider = _FullProvider(_FakeApp())
        self.assertIsInstance(provider, ServiceProvider)
        self.assertIsInstance(provider, IServiceProvider)

# ===========================================================================
# Default hooks
# ===========================================================================

class TestServiceProviderDefaultHooks(TestCase):

    def testBaseRegisterIsANoopReturningNone(self) -> None:
        """
        Return None from the inherited, empty register() implementation.

        Returns
        -------
        None
            This method does not return a value.
        """
        provider = _FullProvider(_FakeApp())
        self.assertIsNone(ServiceProvider.register(provider))
        self.assertEqual(provider.register_calls, 0)

    async def testBaseBootIsAnAwaitableNoopReturningNone(self) -> None:
        """
        Return None from the inherited, empty asynchronous boot() hook.

        Returns
        -------
        None
            This method does not return a value.
        """
        provider = _FullProvider(_FakeApp())
        self.assertIsNone(await ServiceProvider.boot(provider))
        self.assertEqual(provider.boot_calls, 0)

    def testBootIsDeclaredAsACoroutineFunction(self) -> None:
        """
        Declare boot() as a coroutine function, matching the contract.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(inspect.iscoroutinefunction(ServiceProvider.boot))

# ===========================================================================
# Overridden hooks
# ===========================================================================

class TestServiceProviderOverriddenHooks(TestCase):

    async def testRegisterAndBootRunIndependentlyAndRepeatedly(self) -> None:
        """
        Run the overridden hooks independently and tolerate repeated calls.

        Validates that invoking one hook never triggers the other and that
        neither raises when executed more than once.

        Returns
        -------
        None
            This method does not return a value.
        """
        provider = _FullProvider(_FakeApp())

        provider.register()
        provider.register()
        self.assertEqual(provider.register_calls, 2)
        self.assertEqual(provider.boot_calls, 0)

        await provider.boot()
        await provider.boot()
        self.assertEqual(provider.boot_calls, 2)
        self.assertEqual(provider.register_calls, 2)
