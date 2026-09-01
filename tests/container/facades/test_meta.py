from __future__ import annotations
import inspect
from orionis.test import TestCase
from orionis.container.facades.facade import Facade
from orionis.container.facades.meta import FacadeMeta

# ---------------------------------------------------------------------------
# Module-level doubles
# ---------------------------------------------------------------------------

_CONTEXT_VALUE = "ctx-value"
_SERVICE_VERSION = "1.0.0"

class _DummyAsyncContext:
    """Minimal async context manager returned by a proxied method."""

    def __init__(self, value: str) -> None:
        """Store the value yielded when the context is entered."""
        self.value = value
        self.exited = False

    async def __aenter__(self) -> str:
        """Return the fixed value carried by this context."""
        return self.value

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> bool:
        """Record that the context was exited and never suppress errors."""
        self.exited = True
        return False

class _DummyService:
    """Lightweight service used as a stand-in for metaclass tests."""

    version: str = _SERVICE_VERSION

    def greet(self) -> str:
        """Return a greeting string."""
        return "hello"

    def add(self, a: int, b: int) -> int:
        """Return the sum of two integers."""
        return a + b

    async def fetch(self) -> str:
        """Return a value from an asynchronous service method."""
        return "awaited"

    def openContext(self) -> _DummyAsyncContext:
        """Return an async context manager carrying a fixed value."""
        return _DummyAsyncContext(_CONTEXT_VALUE)

class _MetaFacade(Facade):
    """Facade subclass used to exercise the metaclass attribute routing."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """Return the service key for this facade."""
        return "dummy_service"

class _BootedApp:
    """Fake booted application whose make() always returns a _DummyService."""

    isBooted: bool = True  # noqa: N815

    async def make(
        self,
        _key: object,
        *_args: object,
        **_kwargs: object,
    ) -> _DummyService:
        """Return a fresh _DummyService regardless of the requested key."""
        return _DummyService()

class _FacadeStateTestCase(TestCase):
    """
    Base case installing the facade class state around each test.

    Subclasses declare the desired state through class attributes so that no
    test body has to mutate the shared facade globals itself.
    """

    application_double: type | None = None
    pin_service: bool = False

    def setUp(self) -> None:
        """Install the declared facade class state before each test."""
        double = self.application_double
        _MetaFacade._application = None if double is None else double()
        _MetaFacade._pinned_instance = (
            _DummyService() if self.pin_service else None
        )

    def tearDown(self) -> None:
        """Clear the facade class state after each test."""
        _MetaFacade._application = None
        _MetaFacade._pinned_instance = None

# ===========================================================================
# Metaclass wiring
# ===========================================================================

class TestFacadeMetaWiring(_FacadeStateTestCase):

    def testFacadeUsesFacadeMetaAsMetaclass(self) -> None:
        """
        Use FacadeMeta as the metaclass of Facade and of its subclasses.

        Validates the wiring that keeps attribute routing through
        ``__getattr__`` active on every facade.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(Facade, FacadeMeta)
        self.assertIsInstance(_MetaFacade, FacadeMeta)

# ===========================================================================
# Pinned attribute routing
# ===========================================================================

class TestFacadeMetaPinnedAccess(_FacadeStateTestCase):

    pin_service = True

    def testAttributeAccessRoutesToThePinnedInstance(self) -> None:
        """
        Forward attribute access straight to the pinned service instance.

        Both callables and plain attributes must be returned as-is, with no
        dispatcher wrapping and no container resolution.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(_MetaFacade.greet(), "hello")
        self.assertEqual(_MetaFacade.add(3, 4), 7)
        self.assertEqual(_MetaFacade.version, _SERVICE_VERSION)

    def testMissingAttributeOnPinnedInstanceRaisesAttributeError(self) -> None:
        """
        Raise AttributeError for a missing attribute on a pinned facade.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(AttributeError):
            _ = _MetaFacade.does_not_exist

# ===========================================================================
# Deferred dispatcher construction
# ===========================================================================

class TestFacadeMetaDispatcherConstruction(_FacadeStateTestCase):

    def testUnpinnedAccessReturnsADeferredDispatcher(self) -> None:
        """
        Return a synchronous dispatcher when no instance is pinned.

        Calling the dispatcher builds a deferred object that resolves the
        service only once it is awaited or entered as a context manager.

        Returns
        -------
        None
            This method does not return a value.
        """
        dispatcher = _MetaFacade.greet

        self.assertTrue(callable(dispatcher))
        self.assertFalse(inspect.iscoroutinefunction(dispatcher))

        deferred = dispatcher()
        self.assertTrue(hasattr(deferred, "__await__"))
        self.assertTrue(hasattr(deferred, "__aenter__"))
        self.assertTrue(hasattr(deferred, "__aexit__"))

    def testDispatcherIsCachedPerAttributeName(self) -> None:
        """
        Cache one dispatcher per attribute name on the facade class.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIs(_MetaFacade.greet, _MetaFacade.greet)
        self.assertIsNot(_MetaFacade.greet, _MetaFacade.add)

# ===========================================================================
# Deferred dispatcher resolution
# ===========================================================================

class TestFacadeMetaDispatcherResolution(_FacadeStateTestCase):

    application_double = _BootedApp

    async def testAwaitingTheDispatcherCallsTheResolvedMethod(self) -> None:
        """
        Resolve the service and return the call result when awaited.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(await _MetaFacade.greet(), "hello")

    async def testAwaitingTheDispatcherForwardsCallArguments(self) -> None:
        """
        Forward positional arguments to the resolved service method.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(await _MetaFacade.add(2, 5), 7)

    async def testAwaitingTheDispatcherAwaitsAsynchronousResults(self) -> None:
        """
        Await the coroutine returned by an asynchronous service method.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(await _MetaFacade.fetch(), "awaited")

    async def testAwaitingTheDispatcherReturnsNonCallableAttributes(
        self,
    ) -> None:
        """
        Return the plain attribute value when the target is not callable.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(await _MetaFacade.version(), _SERVICE_VERSION)

    async def testDispatcherSupportsAsyncWith(self) -> None:
        """
        Enter and exit an async context manager through an unpinned facade.

        Returns
        -------
        None
            This method does not return a value.
        """
        async with _MetaFacade.openContext() as value:
            self.assertEqual(value, _CONTEXT_VALUE)
