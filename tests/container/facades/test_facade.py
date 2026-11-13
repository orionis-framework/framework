# ruff: noqa: N815, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Facade doubles expose the application isBooted protocol attribute.
from __future__ import annotations
import inspect
from unittest.mock import patch
from orionis.container.facades.facade import Facade
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Module-level doubles
# ---------------------------------------------------------------------------

_ACCESSOR = "dummy_service"


class _DummyService:
    """Lightweight service used as a stand-in for facade tests."""

    def greet(self) -> str:
        """Return a greeting string.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "hello"


class _ConcreteFacade(Facade):
    """Facade subclass with a fixed accessor key."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """Return the service key for this facade.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return _ACCESSOR


class _NoAccessorFacade(Facade):
    """Facade subclass that deliberately omits getFacadeAccessor."""


class _UnbootedApp:
    """Fake application that reports itself as not booted."""

    isBooted: bool = False


class _BootedApp:
    """Fake booted application whose make() always returns a _DummyService."""

    isBooted: bool = True

    async def make(
        self,
        _key: object,
        *_args: object,
        **_kwargs: object,
    ) -> _DummyService:
        """Return a fresh _DummyService regardless of the requested key.

        Parameters
        ----------
        _key : object
            Value supplied for ``_key``.
        *_args : object
            Arguments passed to the wrapped callable.
        **_kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        _DummyService
            Value produced by the helper.
        """
        return _DummyService()


class _CapturingApp:
    """Fake booted application that records the arguments passed to make()."""

    isBooted: bool = True
    captured_key: object = None
    captured_args: tuple[object, ...] = ()
    captured_kwargs: dict[str, object] | None = None

    async def make(
        self,
        key: object,
        *args: object,
        **kwargs: object,
    ) -> _DummyService:
        """Record the forwarded arguments and return a fresh service.

        Parameters
        ----------
        key : object
            Value supplied for ``key``.
        *args : object
            Arguments passed to the wrapped callable.
        **kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        _DummyService
            Value produced by the helper.
        """
        _CapturingApp.captured_key = key
        _CapturingApp.captured_args = args
        _CapturingApp.captured_kwargs = kwargs
        return _DummyService()


class _FacadeStateTestCase(TestCase):
    """
    Base case installing the facade class state around each test.

    Subclasses declare the desired state through class attributes so that no
    test body has to mutate the shared facade globals itself.
    """

    application_double: type | None = None

    def setUp(self) -> None:
        """Install isolated facade state and restore the previous class attributes."""
        super().setUp()
        self.enterContext(
            patch.multiple(
                _CapturingApp,
                captured_key=None,
                captured_args=(),
                captured_kwargs=None,
            ),
        )
        double = self.application_double
        self.enterContext(
            patch.object(
                _ConcreteFacade,
                "_application",
                None if double is None else double(),
            ),
        )
        self.enterContext(patch.object(_ConcreteFacade, "_pinned_instance", None))


# ===========================================================================
# Class attributes
# ===========================================================================


class TestFacadeClassAttributes(_FacadeStateTestCase):
    def testFacadeExposesTheSharedStateAttributes(self) -> None:
        """
        Expose the pinned instance and application slots on the base class.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNone(Facade._pinned_instance)
        self.assertTrue(hasattr(Facade, "_application"))


# ===========================================================================
# Accessor contract
# ===========================================================================


class TestFacadeGetFacadeAccessor(_FacadeStateTestCase):
    def testBaseClassRaisesNotImplementedErrorNamingTheClass(self) -> None:
        """
        Raise NotImplementedError naming the class that lacks an accessor.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(NotImplementedError) as ctx:
            Facade.getFacadeAccessor()
        self.assertIn(Facade.__name__, str(ctx.exception))

    def testUnoverriddenSubclassRaisesNotImplementedError(self) -> None:
        """
        Raise NotImplementedError when a subclass keeps the base accessor.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(NotImplementedError) as ctx:
            _NoAccessorFacade.getFacadeAccessor()
        self.assertIn(_NoAccessorFacade.__name__, str(ctx.exception))

    def testOverriddenSubclassReturnsItsAccessorKey(self) -> None:
        """
        Return the accessor key declared by a concrete facade subclass.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(_ConcreteFacade.getFacadeAccessor(), _ACCESSOR)

    def testAccessorIsDeclaredAsASynchronousClassMethod(self) -> None:
        """
        Keep the accessor synchronous so metaclass routing stays cheap.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(
            inspect.iscoroutinefunction(Facade.getFacadeAccessor),
        )


# ===========================================================================
# resolve() - application not booted
# ===========================================================================


class TestFacadeResolveWithoutBoot(_FacadeStateTestCase):
    application_double = _UnbootedApp

    async def testResolveRaisesRuntimeErrorHintingAtBoot(self) -> None:
        """
        Raise RuntimeError, hinting at boot, when the application is not up.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(RuntimeError) as ctx:
            await _ConcreteFacade.resolve()
        self.assertIn("Boot", str(ctx.exception))

    async def testPinPropagatesResolutionFailures(self) -> None:
        """
        Propagate the RuntimeError raised by resolve() when pinning fails.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(RuntimeError):
            await _ConcreteFacade.pin()
        self.assertIsNone(_ConcreteFacade._pinned_instance)


# ===========================================================================
# resolve() - booted application
# ===========================================================================


class TestFacadeResolveWithBootedApplication(_FacadeStateTestCase):
    application_double = _BootedApp

    async def testResolveReturnsTheServiceInstance(self) -> None:
        """
        Return the resolved service instance when the application is booted.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(await _ConcreteFacade.resolve(), _DummyService)

    async def testResolveReturnsAFreshInstanceOnEveryCall(self) -> None:
        """
        Delegate to the container on every call instead of caching a value.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNot(
            await _ConcreteFacade.resolve(),
            await _ConcreteFacade.resolve(),
        )

    async def testPinCachesTheResolvedInstance(self) -> None:
        """
        Cache the resolved service instance on the facade class.

        Returns
        -------
        None
            No return value.
        """
        await _ConcreteFacade.pin()
        self.assertIsInstance(_ConcreteFacade._pinned_instance, _DummyService)

    async def testUnpinClearsTheCachedInstance(self) -> None:
        """
        Clear the cached instance so normal resolution is restored.

        Returns
        -------
        None
            No return value.
        """
        await _ConcreteFacade.pin()
        _ConcreteFacade.unpin()
        self.assertIsNone(_ConcreteFacade._pinned_instance)


# ===========================================================================
# resolve() - argument forwarding
# ===========================================================================


class TestFacadeResolveArgumentForwarding(_FacadeStateTestCase):
    application_double = _CapturingApp

    async def testForwardsAccessorKeyAndArgumentsToMake(self) -> None:
        """
        Forward the accessor key and every extra argument to make().

        Returns
        -------
        None
            No return value.
        """
        await _ConcreteFacade.resolve("extra", flag=True)

        self.assertEqual(_CapturingApp.captured_key, _ACCESSOR)
        self.assertEqual(_CapturingApp.captured_args, ("extra",))
        self.assertEqual(_CapturingApp.captured_kwargs, {"flag": True})


# ===========================================================================
# resolve() - lazy application bootstrap
# ===========================================================================


class TestFacadeLazyApplication(_FacadeStateTestCase):
    async def testResolveInitialisesTheSharedApplicationLazily(self) -> None:
        """
        Build the shared application on the first resolve without a cache.

        The constructor returns a controlled unbooted application. Resolution
        must cache that object and then raise the specific boot guard error.

        Returns
        -------
        None
            No return value.
        """
        application = _UnbootedApp()
        with (
            patch(
                "orionis.foundation.application.Application",
                return_value=application,
            ) as factory,
            self.assertRaisesRegex(RuntimeError, "Application not booted"),
        ):
            await _ConcreteFacade.resolve()
        factory.assert_called_once_with()
        self.assertIs(_ConcreteFacade._application, application)

    def testUnpinIsIdempotentWhenNothingIsPinned(self) -> None:
        """
        Keep the pinned slot empty when unpin() runs without a cached value.

        Returns
        -------
        None
            No return value.
        """
        _ConcreteFacade.unpin()
        self.assertIsNone(_ConcreteFacade._pinned_instance)
