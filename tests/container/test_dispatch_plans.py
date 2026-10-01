import asyncio
import gc
import weakref
from unittest.mock import patch
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.container.entities.invocation import callable_plan
from orionis.http.request import Request
from orionis.schemas.schema import Schema
from orionis.test import TestCase

class _Service:
    """Represent an injectable service."""

class _Replacement(_Service):
    """Represent a replacement service registration."""

class _Controller:
    """Receive a service in an action with explicit arguments."""

    async def handle(self, service: _Service, count: int = 2) -> tuple:
        """Return the resolved service and count.

        Parameters
        ----------
        service : _Service
            Dependency resolved within the active container.
        count : int, optional
            Explicit or default count.

        Returns
        -------
        tuple
            Dependency and count.
        """
        return service, count

class _Payload(Schema):
    """Represent a schema requiring an asynchronous body read."""

    value: int

class _ScopedService:
    """Suspend DI while obtaining a payload."""

    def __init__(self, payload: _Payload) -> None:
        """Store the validated payload.

        Parameters
        ----------
        payload : _Payload
            Request-owned schema value.

        Returns
        -------
        None
            The payload is assigned to the service.
        """
        self.payload = payload

class _Request(Request):
    """Gate body reads using events controlled by a test."""

    def __init__(self, entered: asyncio.Queue, release: asyncio.Event) -> None:
        """Store the shared read gate.

        Parameters
        ----------
        entered : asyncio.Queue
            Receives a marker whenever a body read starts.
        release : asyncio.Event
            Allows a body read to complete.

        Returns
        -------
        None
            The request is ready for schema injection.
        """
        self.entered = entered
        self.release = release

    async def data(self) -> dict[str, int]:
        """Publish a read marker and wait for the test gate.

        Returns
        -------
        dict[str, int]
            Payload consumed by the schema validator.
        """
        self.entered.put_nowait(None)
        await self.release.wait()
        return {"value": 1}

class _MultiProvider:
    """Publish two services while boot remains under test control."""

    container: Container
    entered: asyncio.Event
    release: asyncio.Event
    registrations = 0
    boots = 0

    def register(self) -> None:
        """Register both services and their aliases.

        Returns
        -------
        None
            Services are registered once per provider instance.
        """
        type(self).registrations += 1
        self.container.singleton(None, _Service, alias="first")
        self.container.singleton(None, _Replacement, alias="second")

    async def boot(self) -> None:
        """Resolve an owned service and await readiness.

        Returns
        -------
        None
            The provider is ready after the event is released.
        """
        type(self).boots += 1
        await asyncio.gather(self.container.make("first"))
        self.entered.set()
        await self.release.wait()

class TestDispatchPlans(TestCase):
    """Keep metadata reusable while dependencies and lifetimes stay dynamic."""

    def setUp(self) -> None:
        """Create an isolated container outside the runner's scope.

        Returns
        -------
        None
            Registrations belong to this test's container.
        """
        self.token = ScopedContext.setCurrentScope(None)
        self.container = object.__new__(Container)
        Container.__init__(self.container)

    def tearDown(self) -> None:
        """Restore the caller's scope.

        Returns
        -------
        None
            The test's context is released.
        """
        ScopedContext.reset(self.token)

    async def testPlansDoNotRetainControllers(self) -> None:
        """Release controllers after invoking a shared method plan.

        Returns
        -------
        None
            No receiver survives solely through the metadata cache.
        """
        self.container.singleton(None, _Service)
        references = []
        for _ in range(1100):
            controller = await self.container.build(_Controller)
            references.append(weakref.ref(controller))
            await self.container.call(controller, "handle")
        del controller
        gc.collect()
        self.assertFalse(any(reference() is not None for reference in references))

    async def testWarmPlansHonorBindingAndArgumentOverrides(self) -> None:
        """Read current bindings and explicit keyword values on each invocation.

        Returns
        -------
        None
            Warm plans use replacements without modifying caller dictionaries.
        """
        first = _Service()
        self.container.instance(_Service, first)
        controller = _Controller()
        self.assertEqual(await self.container.call(controller, "handle"), (first, 2))
        self.container.singleton(_Service, _Replacement, override=True)
        replacement, count = await self.container.call(controller, "handle", count=9)
        self.assertIsInstance(replacement, _Replacement)
        self.assertEqual(count, 9)
        arguments = {"service": first, "count": 8}
        self.assertEqual(await self.container.call(controller, "handle", **arguments),
                         (first, 8))
        self.assertEqual(arguments, {"service": first, "count": 8})

    async def testWarmPlanSkipsRepeatedCoroutineIntrospection(self) -> None:
        """Reuse cached coroutine metadata during invocation.

        Returns
        -------
        None
            Invocation succeeds without checking the callable again.
        """
        controller = _Controller()
        callable_plan(controller.handle)
        with patch("orionis.container.entities.invocation.inspect.iscoroutinefunction",
                   side_effect=AssertionError("Unexpected introspection")):
            service, count = await self.container.call(controller, "handle")
        self.assertIsInstance(service, _Service)
        self.assertEqual(count, 2)

    async def testReplacedMethodsAndConstructorsGetNewPlans(self) -> None:
        """Observe callable replacements without reusing obsolete metadata.

        Returns
        -------
        None
            New constructor and action defaults are honored immediately.
        """

        class MutableController:
            """Expose a controller whose callable descriptors can change."""

            def action(self, value: int = 1) -> int:
                """Return the action value.

                Parameters
                ----------
                value : int, optional
                    Value provided by DI.

                Returns
                -------
                int
                    Provided value.
                """
                return value

        def replacement_action(self, value: int = 9) -> int:  # noqa: ARG001
            """Return the replacement action value.

            Parameters
            ----------
            self : MutableController
                Bound controller instance.
            value : int, optional
                Value supplied by DI.

            Returns
            -------
            int
                Provided value.
            """
            return value

        def replacement_constructor(self, value: int = 4) -> None:
            """Store the replacement constructor value.

            Parameters
            ----------
            self : MutableController
                Instance initialized by this constructor.
            value : int, optional
                Value supplied by DI.

            Returns
            -------
            None
                The constructor value is stored on the instance.
            """
            self.value = value

        controller = await self.container.build(MutableController)
        self.assertEqual(await self.container.call(controller, "action"), 1)
        MutableController.action = replacement_action
        MutableController.__init__ = replacement_constructor
        self.assertEqual(await self.container.call(controller, "action"), 9)
        self.assertEqual((await self.container.build(MutableController)).value, 4)

    async def testIndependentScopesConstructConcurrently(self) -> None:
        """Start construction in two scopes before either body read completes.

        Returns
        -------
        None
            Separate scopes overlap and receive distinct services.
        """
        entered = asyncio.Queue()
        release = asyncio.Event()
        self.container.instance(Request, _Request(entered, release))
        self.container.scoped(None, _ScopedService)

        async def resolve() -> _ScopedService:
            """Resolve one service within a new scope.

            Returns
            -------
            _ScopedService
                Service owned by the new scope.
            """
            async with self.container.beginScope():
                return await self.container.make(_ScopedService)

        async with asyncio.TaskGroup() as group:
            first = group.create_task(resolve())
            second = group.create_task(resolve())
            try:
                async with asyncio.timeout(2):
                    await entered.get()
                    await entered.get()
            finally:
                release.set()
        self.assertIsNot(first.result(), second.result())

    async def testCancelledScopedConstructionCanRetry(self) -> None:
        """Release the construction lock when its owner is cancelled.

        Returns
        -------
        None
            A later resolver builds and caches the service within the same scope.
        """
        entered = asyncio.Queue()
        release = asyncio.Event()
        self.container.instance(Request, _Request(entered, release))
        self.container.scoped(None, _ScopedService)
        async with self.container.beginScope():
            task = asyncio.create_task(self.container.make(_ScopedService))
            await entered.get()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            release.set()
            resolved = await self.container.make(_ScopedService)
            self.assertIs(resolved, await self.container.make(_ScopedService))

    def _configureProvider(self) -> None:
        """Configure the multi-service deferred provider fixture.

        Returns
        -------
        None
            Both aliases refer to the same provider identity.
        """
        _MultiProvider.container = self.container
        _MultiProvider.entered = asyncio.Event()
        _MultiProvider.release = asyncio.Event()
        _MultiProvider.registrations = 0
        _MultiProvider.boots = 0
        metadata = {"module": __name__, "class": "_MultiProvider"}
        self.container._deferred_providers = {
            "first": metadata,
            "second": metadata,
            f"{_Service.__module__}.{_Service.__name__}": metadata,
            f"{_Replacement.__module__}.{_Replacement.__name__}": metadata,
        }

    async def testProviderContractsShareReadiness(self) -> None:
        """Wait for a provider before returning another registered contract.

        Returns
        -------
        None
            Both contracts resolve after exactly one register and boot.
        """
        self._configureProvider()
        async with asyncio.TaskGroup() as group:
            first = group.create_task(self.container.make("first"))
            await _MultiProvider.entered.wait()
            second = group.create_task(self.container.make("second"))
            by_type = group.create_task(self.container.make(_Replacement))
            try:
                await asyncio.sleep(0)
                self.assertFalse(second.done())
                self.assertFalse(by_type.done())
            finally:
                _MultiProvider.release.set()
        self.assertIsInstance(first.result(), _Service)
        self.assertIs(second.result(), by_type.result())
        self.assertEqual(_MultiProvider.registrations, 1)
        self.assertEqual(_MultiProvider.boots, 1)

    async def testCancelledProviderBootReusesRegistration(self) -> None:
        """Retry cancelled boot without registering published services twice.

        Returns
        -------
        None
            The next contract resolver completes the same provider instance.
        """
        self._configureProvider()
        task = asyncio.create_task(self.container.make("first"))
        await _MultiProvider.entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        _MultiProvider.release.set()
        self.assertIsInstance(await self.container.make("second"), _Replacement)
        self.assertEqual(_MultiProvider.registrations, 1)
        self.assertEqual(_MultiProvider.boots, 2)

    async def testUndeclaredAliasStillWaitsForItsDeclaredContract(self) -> None:
        """Coordinate aliases registered by a provider advertising only types.

        Returns
        -------
        None
            The alias cannot expose a service before its provider is ready.
        """
        self._configureProvider()
        del self.container._deferred_providers["second"]
        async with asyncio.TaskGroup() as group:
            group.create_task(self.container.make("first"))
            await _MultiProvider.entered.wait()
            second = group.create_task(self.container.make("second"))
            try:
                await asyncio.sleep(0)
                self.assertFalse(second.done())
            finally:
                _MultiProvider.release.set()
        self.assertIsInstance(second.result(), _Replacement)
