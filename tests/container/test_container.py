import asyncio
import threading
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from typing import Self
from orionis.test import TestCase
from orionis.container.container import Container
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.container.contracts.container import IContainer
from orionis.container.entities.binding import Binding
from orionis.container.enums.lifetimes import Lifetime
from orionis.container.exceptions.container import CircularDependencyException
from orionis.http.request import Request
from orionis.introspection.dependencies.entities.argument import Argument
from orionis.schemas.schema import Schema

# ---------------------------------------------------------------------------
# Module-level domain helpers
# (must live at module scope so qualified names are stable for DI resolution)
# ---------------------------------------------------------------------------

_NOT_A_CLASS = "not_a_class"

class _Plain:
    """No-dependency service."""

class _IAbstract(ABC):  # noqa: B024
    """Minimal abstract contract."""

class _ConcreteA(_Plain, _IAbstract):
    """Satisfies both _Plain and _IAbstract."""

class _NeedsPlain:
    """Service with a single positional _Plain dependency."""

    def __init__(self, dep: _Plain) -> None:
        """Store the injected dependency."""
        self.dep = dep

class _NeedsKeywordPlain:
    """Service with a single keyword-only _Plain dependency."""

    def __init__(self, *, dep: _Plain) -> None:
        """Store the injected dependency."""
        self.dep = dep

class _NeedsBuiltin:
    """Service annotated with a builtin type and no default value."""

    def __init__(self, count: int) -> None:
        """Store the builtin argument that the container cannot resolve."""
        self.count = count

class _NeedsDefault:
    """Service whose only argument carries a default value."""

    def __init__(self, flag: str = "fallback") -> None:
        """Store the argument resolved from its own default."""
        self.flag = flag

# Circular dependency pair — patched after both classes are defined so that
# annotations are real class references (not strings), which the reflection
# engine can resolve correctly.
class _CircA:
    """Circular dep node A — constructor patched below."""

class _CircB:
    """Circular dep node B — depends on _CircA."""

    def __init__(self, a: _CircA) -> None:
        """Store the injected node A."""
        self.a = a

def _circa_init(self, b: _CircB) -> None:
    """Patch the constructor that closes the A to B to A cycle."""
    self.b = b

_CircA.__init__ = _circa_init  # type: ignore[method-assign]

class _Host:
    """Object used to test call() DI dispatch."""

    non_callable: str = "string_value"

    def greet(self) -> str:
        """Return a fixed greeting."""
        return "hello"

    def echo(self, dep: _Plain) -> _Plain:
        """Return the injected dependency."""
        return dep

def _fn_no_dep() -> str:
    """Return a constant from a dependency-free function."""
    return "ok"

def _fn_with_dep(dep: _Plain) -> _Plain:
    """Return the dependency injected into a synchronous function."""
    return dep

async def _afn_no_dep() -> str:
    """Return a constant from a dependency-free coroutine function."""
    return "async_ok"

async def _afn_with_dep(dep: _Plain) -> _Plain:
    """Return the dependency injected into a coroutine function."""
    return dep

# ---------------------------------------------------------------------------
# Schema resolution helpers
# ---------------------------------------------------------------------------

_SCHEMA_NAME = "orionis"

class _StubRequest(Request):
    """Request double returning a fixed body payload."""

    def __init__(self) -> None:
        """Skip the transport wiring required by the real request."""

    async def data(self) -> dict[str, object]:
        """Return the canned request payload."""
        return {"name": _SCHEMA_NAME}

class _PayloadSchema(Schema):
    """Schema declaring the single field carried by the stub request."""

    name: str

class _NeedsSchema:
    """Service receiving a schema as a positional constructor argument."""

    def __init__(self, payload: _PayloadSchema) -> None:
        """Store the validated schema payload."""
        self.payload = payload

class _NeedsKeywordSchema:
    """Service receiving a schema as a keyword-only constructor argument."""

    def __init__(self, *, payload: _PayloadSchema) -> None:
        """Store the validated schema payload."""
        self.payload = payload

# ---------------------------------------------------------------------------
# Concurrency helpers
# ---------------------------------------------------------------------------

_CONCURRENT_TASKS = 8
_CONCURRENT_THREADS = 32
_CYCLE_TIMEOUT = 5.0

class _SlowRequest(Request):
    """Request double that yields control before answering."""

    def __init__(self) -> None:
        """Skip the transport wiring required by the real request."""

    async def data(self) -> dict[str, object]:
        """Suspend once, then return the canned request payload."""
        await asyncio.sleep(0)
        return {"name": _SCHEMA_NAME}

class _SuspendingSingleton:
    """Singleton whose construction suspends on a schema argument."""

    constructions = 0

    def __init__(self, payload: _PayloadSchema) -> None:
        """Count the construction and store the validated payload."""
        _SuspendingSingleton.constructions += 1
        self.payload = payload

class _SuspendingScoped:
    """Scoped service whose construction suspends on a schema argument."""

    constructions = 0

    def __init__(self, payload: _PayloadSchema) -> None:
        """Count the construction and store the validated payload."""
        _SuspendingScoped.constructions += 1
        self.payload = payload

def _locks_from_two_loops(container: Container) -> tuple[object, object]:
    """
    Build the creation lock of one key on two different event loops.

    Parameters
    ----------
    container : Container
        Container whose private lock registry is exercised.

    Returns
    -------
    tuple[object, object]
        The lock produced by the first loop and the one produced by a second,
        independent loop.
    """
    async def take() -> object:
        return container._Container__creationLock(_Plain)

    def capture() -> tuple[object, object]:
        return asyncio.run(take()), asyncio.run(take())

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(capture).result()

# ---------------------------------------------------------------------------
# Deferred provider helpers
# ---------------------------------------------------------------------------

_ASYNC_ALIAS = "deferred_async_service"
_SYNC_ALIAS = "deferred_sync_service"

class _DeferredService:
    """Service published by the deferred provider doubles."""

class _DeferredKwService:
    """Dependency published by the deferred provider double."""

class _AsyncDeferredProvider:
    """Deferred provider double exposing an asynchronous boot hook."""

    container: Container | None = None
    register_calls: int = 0
    boot_calls: int = 0

    @classmethod
    def reset(cls, container: Container | None) -> None:
        """
        Attach a container to the double and clear its counters.

        Parameters
        ----------
        container : Container | None
            Container that ``register()`` must populate, or None to detach.

        Returns
        -------
        None
            This method does not return a value.
        """
        cls.container = container
        cls.register_calls = 0
        cls.boot_calls = 0

    def register(self) -> None:
        """Publish the deferred alias into the attached container."""
        _AsyncDeferredProvider.register_calls += 1
        if _AsyncDeferredProvider.container is not None:
            _AsyncDeferredProvider.container.transient(
                None, _DeferredService, alias=_ASYNC_ALIAS,
            )

    async def boot(self) -> None:
        """Record that the asynchronous boot hook ran."""
        _AsyncDeferredProvider.boot_calls += 1

class _SyncDeferredProvider:
    """Deferred provider double exposing a synchronous boot hook."""

    container: Container | None = None
    boot_calls: int = 0

    @classmethod
    def reset(cls, container: Container | None) -> None:
        """
        Attach a container to the double and clear its counters.

        Parameters
        ----------
        container : Container | None
            Container that ``register()`` must populate, or None to detach.

        Returns
        -------
        None
            This method does not return a value.
        """
        cls.container = container
        cls.boot_calls = 0

    def register(self) -> None:
        """Publish the deferred alias into the attached container."""
        if _SyncDeferredProvider.container is not None:
            _SyncDeferredProvider.container.transient(
                None, _DeferredService, alias=_SYNC_ALIAS,
            )

    def boot(self) -> None:
        """Record that the synchronous boot hook ran."""
        _SyncDeferredProvider.boot_calls += 1

class _DependencyProvider:
    """Deferred provider double binding a constructor dependency."""

    container: Container | None = None
    register_calls: int = 0

    @classmethod
    def reset(cls, container: Container | None) -> None:
        """
        Attach a container to the double and clear its counters.

        Parameters
        ----------
        container : Container | None
            Container that ``register()`` must populate, or None to detach.

        Returns
        -------
        None
            This method does not return a value.
        """
        cls.container = container
        cls.register_calls = 0

    def register(self) -> None:
        """Publish the deferred dependency into the attached container."""
        _DependencyProvider.register_calls += 1
        if _DependencyProvider.container is not None:
            _DependencyProvider.container.transient(None, _DeferredKwService)

    async def boot(self) -> None:
        """Suspend once so concurrent resolutions can interleave."""
        await asyncio.sleep(0)

class _NeedsDeferredDep:
    """Service depending on a type published by a deferred provider."""

    def __init__(self, dep: _DeferredKwService) -> None:
        """Store the deferred dependency."""
        self.dep = dep

_TEST_MODULE = __name__
_DEFERRED_DEP_KEY = (
    f"{_DeferredKwService.__module__}.{_DeferredKwService.__name__}"
)
_DEFERRED_REGISTRY: dict[str, dict[str, str]] = {
    _ASYNC_ALIAS: {"module": _TEST_MODULE, "class": "_AsyncDeferredProvider"},
    _SYNC_ALIAS: {"module": _TEST_MODULE, "class": "_SyncDeferredProvider"},
    _DEFERRED_DEP_KEY: {
        "module": _TEST_MODULE,
        "class": "_DependencyProvider",
    },
}

# ---------------------------------------------------------------------------
# Singleton race helpers
# ---------------------------------------------------------------------------

class _RaceLock:
    """Lock double publishing a competing singleton while it is held."""

    __slots__ = ("entries", "owner")

    def __init__(self) -> None:
        """Start the lock double unbound and never entered."""
        self.entries: int = 0
        self.owner: type | None = None

    def bindTo(self, owner: type | None) -> None:
        """
        Bind the container subclass that must win the singleton race.

        Parameters
        ----------
        owner : type | None
            Container subclass published on the next acquisition, or None to
            disarm the double.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.owner = owner
        self.entries = 0

    def __enter__(self) -> Self:
        """
        Publish the competing instance as soon as the lock is acquired.

        Returns
        -------
        Self
            The lock double itself, mirroring ``threading.RLock`` semantics.
        """
        self.entries += 1
        owner = self.owner
        if owner is not None:
            owner._instances[owner] = object.__new__(owner)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        """
        Release the lock without ever suppressing exceptions.

        Parameters
        ----------
        exc_type : object
            Exception type raised inside the block, if any.
        exc : object
            Exception instance raised inside the block, if any.
        tb : object
            Traceback of the raised exception, if any.

        Returns
        -------
        bool
            Always False, so exceptions propagate untouched.
        """
        return False

_RACE_LOCK = _RaceLock()

class _SingletonRaceProbe(Container):
    """Container subclass whose lock publishes a competing instance."""

    _lock = _RACE_LOCK  # type: ignore[assignment]

class _UnknownLifetimeBinding:
    """Binding double carrying a lifetime outside the Lifetime enum."""

    __slots__ = ("concrete", "contract", "lifetime")

    def __init__(self) -> None:
        """Build a binding double with an unrecognised lifetime."""
        self.contract: type = _Plain
        self.concrete: type = _Plain
        self.lifetime: str = "unsupported"

# ---------------------------------------------------------------------------
# Container isolation factory
# ---------------------------------------------------------------------------

def _fresh() -> Container:
    """
    Return an isolated Container instance.

    Every call executes a ``class`` statement, producing a *new* class object.
    Container stores singletons keyed by class, so each returned container has
    its own, completely private state.

    Returns
    -------
    Container
        A brand-new container instance with no registrations.
    """
    class _Isolated(Container):
        pass

    return _Isolated()

class _ScopelessTestCase(TestCase):
    """
    Base case detaching whatever container scope the runner keeps active.

    The CLI runner resolves its own services inside a long-lived scope, and
    that scope object is shared by every test context. Detaching it keeps
    registrations global and prevents state from leaking between tests.
    """

    def setUp(self) -> None:
        """Detach the ambient scope so registrations land globally."""
        self._scope_token = ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """Restore the ambient scope captured before the test."""
        ScopedContext.reset(self._scope_token)

# ===========================================================================
# Container - singleton pattern and contract
# ===========================================================================

class TestContainerSingleton(_ScopelessTestCase):

    def testSameClassReturnsSameInstance(self) -> None:
        """
        Return the same object when a Container subclass is built twice.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _S(Container):
            pass

        self.assertIs(_S(), _S())

    def testDifferentSubclassesYieldDifferentInstances(self) -> None:
        """
        Produce independent singletons for two distinct Container subclasses.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _X(Container):
            pass

        class _Y(Container):
            pass

        self.assertIsNot(_X(), _Y())

    def testContainerImplementsIContainer(self) -> None:
        """
        Satisfy the IContainer contract with a concrete Container instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_fresh(), IContainer)

    def testRepeatedInitialisationKeepsTheOriginalState(self) -> None:
        """
        Skip re-initialisation when the singleton is constructed again.

        Validates that the guard in ``__init__`` preserves registrations made
        through a previously returned reference to the same singleton.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _S(Container):
            pass

        _S().transient(None, _Plain)
        self.assertTrue(_S().bound(_Plain))

class TestContainerSingletonRace(_ScopelessTestCase):

    def setUp(self) -> None:
        """Arm the lock double so the probe observes a competing instance."""
        super().setUp()
        _RACE_LOCK.bindTo(_SingletonRaceProbe)

    def tearDown(self) -> None:
        """Disarm the lock double and drop the probe singleton."""
        _RACE_LOCK.bindTo(None)
        Container._instances.pop(_SingletonRaceProbe, None)
        super().tearDown()

    def testConstructionReturnsTheInstancePublishedUnderTheLock(self) -> None:
        """
        Return the instance published by a competing caller under the lock.

        Validates the double-checked locking branch of ``__new__``, which must
        discard its own construction when another caller already stored a
        singleton while the lock was being acquired.

        Returns
        -------
        None
            This method does not return a value.
        """
        published = _SingletonRaceProbe()

        self.assertEqual(_RACE_LOCK.entries, 1)
        self.assertIs(published, Container._instances[_SingletonRaceProbe])
        self.assertIsInstance(published, _SingletonRaceProbe)

# ===========================================================================
# instance()
# ===========================================================================

class TestContainerInstance(_ScopelessTestCase):

    def testRegisterInstanceReturnsTrue(self) -> None:
        """
        Return True from instance() on a successful registration.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        self.assertTrue(_fresh().instance(None, _Svc()))

    def testRegisterInstanceWithExplicitAbstract(self) -> None:
        """
        Accept an explicit abstract contract when registering an instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(_fresh().instance(_IAbstract, _ConcreteA()))

    def testRegisterClassTypeRaisesTypeError(self) -> None:
        """
        Raise TypeError when instance() receives a class instead of an object.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.instance(None, _Plain)  # type: ignore[arg-type]

    def testRegisterInstanceMismatchRaisesTypeError(self) -> None:
        """
        Raise TypeError for an instance that does not implement the abstract.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.instance(_IAbstract, _Plain())

    def testRegisterInstanceWithNonClassAbstractRaisesTypeError(self) -> None:
        """
        Raise TypeError when the abstract passed to instance() is not a class.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.instance(_NOT_A_CLASS, _Plain())  # type: ignore[arg-type]

    def testRegisterDuplicateWithoutOverrideRaisesValueError(self) -> None:
        """
        Raise ValueError when the same abstract is registered twice.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        c = _fresh()
        c.instance(None, _Svc())
        with self.assertRaises(ValueError):
            c.instance(None, _Svc())

    def testRegisterDuplicateWithOverrideSucceeds(self) -> None:
        """
        Replace an existing registration when override is requested.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        c = _fresh()
        c.instance(None, _Svc())
        self.assertTrue(c.instance(None, _Svc(), override=True))

    async def testRegisterInstanceWithAliasResolvesByAlias(self) -> None:
        """
        Resolve a globally registered instance through its alias.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        service = _Plain()
        self.assertTrue(c.instance(None, service, alias="plain_instance"))
        self.assertIs(await c.make("plain_instance"), service)

class TestContainerInstanceInsideScope(_ScopelessTestCase):

    async def testInstanceIsStoredInTheActiveScope(self) -> None:
        """
        Store an instance in the active scope instead of the global registry.

        Validates that ``bound()`` also reports the scoped registration.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        service = _Plain()
        async with c.beginScope() as scope:
            self.assertTrue(c.instance(None, service))
            self.assertIs(scope[_Plain], service)
            self.assertTrue(c.bound(_Plain))

    async def testDuplicateInstanceInsideScopeRaisesValueError(self) -> None:
        """
        Raise ValueError when the same abstract is registered twice in a scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        async with c.beginScope():
            c.instance(None, _Plain())
            with self.assertRaises(ValueError):
                c.instance(None, _Plain())

    async def testInstanceOverrideInsideScopeReplacesTheEntry(self) -> None:
        """
        Replace a scoped registration when override is requested.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        replacement = _Plain()
        async with c.beginScope() as scope:
            c.instance(None, _Plain())
            self.assertTrue(c.instance(None, replacement, override=True))
            self.assertIs(scope[_Plain], replacement)

    async def testInstanceWithAliasInsideScopeRaisesValueError(self) -> None:
        """
        Raise ValueError when registering an aliased instance inside a scope.

        Alias registration is only allowed globally, never inside a scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        async with c.beginScope():
            with self.assertRaises(ValueError):
                c.instance(None, _Plain(), alias="scoped_alias")

# ===========================================================================
# transient()
# ===========================================================================

class TestContainerTransient(_ScopelessTestCase):

    def testTransientReturnsTrue(self) -> None:
        """
        Return True from transient() on a valid registration.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(_fresh().transient(None, _Plain))

    def testTransientWithoutAbstractSelfBinds(self) -> None:
        """
        Bind the concrete class to itself when no abstract is supplied.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _Plain)
        self.assertTrue(c.bound(_Plain))

    def testTransientWithAbstractBindsContract(self) -> None:
        """
        Register the abstract contract when one is supplied explicitly.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(_IAbstract, _ConcreteA)
        self.assertTrue(c.bound(_IAbstract))

    def testTransientConcreteNotClassRaisesTypeError(self) -> None:
        """
        Raise TypeError when the concrete argument is not a class.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.transient(None, _NOT_A_CLASS)  # type: ignore[arg-type]

    def testTransientAbstractNotClassRaisesTypeError(self) -> None:
        """
        Raise TypeError when the abstract argument is not a class.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.transient(_NOT_A_CLASS, _Plain)  # type: ignore[arg-type]

    def testTransientConcreteNotClassWithAbstractRaisesTypeError(self) -> None:
        """
        Raise TypeError when only the concrete argument is not a class.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.transient(_IAbstract, _NOT_A_CLASS)  # type: ignore[arg-type]

    def testTransientConcreteNotImplementingAbstractRaisesTypeError(
        self,
    ) -> None:
        """
        Raise TypeError when the concrete does not implement the abstract.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.transient(_IAbstract, _Plain)

    def testTransientDuplicateRaisesValueError(self) -> None:
        """
        Raise ValueError when the same abstract is registered twice.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _Plain)
        with self.assertRaises(ValueError):
            c.transient(None, _Plain)

    async def testTransientMakeReturnsNewInstanceEachTime(self) -> None:
        """
        Return a distinct object from every make() on a transient binding.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        c = _fresh()
        c.transient(None, _Svc)
        self.assertIsNot(await c.make(_Svc), await c.make(_Svc))

# ===========================================================================
# singleton()
# ===========================================================================

class TestContainerSingletonBinding(_ScopelessTestCase):

    def testSingletonReturnsTrue(self) -> None:
        """
        Return True from singleton() on a valid registration.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(_fresh().singleton(None, _Plain))

    async def testSingletonMakeReturnsSameInstanceEveryTime(self) -> None:
        """
        Return the same cached object from every make() on a singleton.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        c = _fresh()
        c.singleton(None, _Svc)
        self.assertIs(await c.make(_Svc), await c.make(_Svc))

    def testSingletonDuplicateRaisesValueError(self) -> None:
        """
        Raise ValueError when the same singleton is registered twice.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.singleton(None, _Plain)
        with self.assertRaises(ValueError):
            c.singleton(None, _Plain)

# ===========================================================================
# scoped()
# ===========================================================================

class TestContainerScopedBinding(_ScopelessTestCase):

    def testScopedReturnsTrue(self) -> None:
        """
        Return True from scoped() on a valid registration.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(_fresh().scoped(None, _Plain))

    async def testScopedServiceResolvesInsideScope(self) -> None:
        """
        Resolve a scoped service successfully within an active scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.scoped(None, _Plain)
        async with c.beginScope():
            self.assertIsInstance(await c.make(_Plain), _Plain)

    async def testScopedServiceReturnsSameInstanceWithinScope(self) -> None:
        """
        Return the same instance for repeated make() calls in one scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.scoped(None, _Plain)
        async with c.beginScope():
            self.assertIs(await c.make(_Plain), await c.make(_Plain))

    async def testScopedServiceRaisesRuntimeErrorOutsideScope(self) -> None:
        """
        Raise RuntimeError when a scoped service is resolved without a scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.scoped(None, _Plain)
        with self.assertRaises(RuntimeError):
            await c.make(_Plain)

# ===========================================================================
# bound()
# ===========================================================================

class TestContainerBound(_ScopelessTestCase):

    def testBoundReturnsTrueAfterTransientRegistration(self) -> None:
        """
        Return True from bound() right after a transient registration.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _Plain)
        self.assertTrue(c.bound(_Plain))

    def testBoundReturnsFalseForUnregisteredType(self) -> None:
        """
        Return False from bound() for a type that was never registered.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertFalse(_fresh().bound(_Plain))

    def testBoundReturnsTrueForRegisteredAlias(self) -> None:
        """
        Return True from bound() when queried with a registered alias.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _Plain, alias="plain_svc")
        self.assertTrue(c.bound("plain_svc"))

    def testBoundReturnsFalseForUnknownAlias(self) -> None:
        """
        Return False from bound() for an alias that was never registered.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertFalse(_fresh().bound("nonexistent_alias"))

    def testBoundReturnsTrueAfterInstanceRegistration(self) -> None:
        """
        Return True from bound() after registering an object instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        c = _fresh()
        c.instance(None, _Svc())
        self.assertTrue(c.bound(_Svc))

# ===========================================================================
# Alias validation
# ===========================================================================

class TestContainerAlias(_ScopelessTestCase):

    def testEmptyAliasRaisesValueError(self) -> None:
        """
        Raise ValueError for an alias made only of whitespace.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(ValueError):
            c.transient(None, _Plain, alias="   ")

    def testNonStringAliasRaisesTypeError(self) -> None:
        """
        Raise TypeError when the alias is not a string.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            c.transient(None, _Plain, alias=123)  # type: ignore[arg-type]

    def testAliasIsStrippedBeforeRegistration(self) -> None:
        """
        Strip surrounding whitespace from an alias before registering it.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _Plain, alias="  padded_alias  ")
        self.assertTrue(c.bound("padded_alias"))

    def testDuplicateAliasRaisesValueError(self) -> None:
        """
        Raise ValueError when two registrations reuse the same alias.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _Plain, alias="svc")
        with self.assertRaises(ValueError):
            c.transient(_IAbstract, _ConcreteA, alias="svc")

    async def testMakeByAliasReturnsCorrectType(self) -> None:
        """
        Return an instance of the registered type when resolving by alias.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _Plain, alias="my_plain")
        self.assertIsInstance(await c.make("my_plain"), _Plain)

# ===========================================================================
# override parameter
# ===========================================================================

class TestContainerOverride(_ScopelessTestCase):

    def testOverrideFalseRaisesValueError(self) -> None:
        """
        Raise ValueError when a contract is re-registered with override False.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.singleton(None, _Plain)
        with self.assertRaises(ValueError):
            c.singleton(None, _Plain, override=False)

    def testOverrideTrueReplacesExistingBinding(self) -> None:
        """
        Replace an existing binding when override is requested.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.singleton(_IAbstract, _ConcreteA)
        self.assertTrue(c.singleton(_IAbstract, _ConcreteA, override=True))

# ===========================================================================
# make()
# ===========================================================================

class TestContainerMake(_ScopelessTestCase):

    async def testMakeTransientReturnsNewInstanceEachCall(self) -> None:
        """
        Return a different object from every make() on a transient binding.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        c = _fresh()
        c.transient(None, _Svc)
        self.assertIsNot(await c.make(_Svc), await c.make(_Svc))

    async def testMakeSingletonReturnsSameObjectEachCall(self) -> None:
        """
        Return the cached instance from every make() on a singleton binding.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Svc:
            pass

        c = _fresh()
        c.singleton(None, _Svc)
        self.assertIs(await c.make(_Svc), await c.make(_Svc))

    async def testMakeUnregisteredClassAutoResolves(self) -> None:
        """
        Auto-resolve an unregistered class that needs no constructor argument.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertIsInstance(await c.make(_Plain), _Plain)

    async def testMakeUnregisteredStringRaisesValueError(self) -> None:
        """
        Raise ValueError when make() receives an unknown alias string.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(ValueError):
            await c.make("ghost_service")

    async def testMakeNonTypeKeyRaisesValueError(self) -> None:
        """
        Raise ValueError when make() receives a key that is not a class.

        A non-string, non-class key cannot be auto-built, so the container
        must report it as an unregistered service.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(ValueError):
            await c.make(123)  # type: ignore[arg-type]

    async def testMakeAbstractContractReturnsConcreteInstance(self) -> None:
        """
        Return an instance of the concrete class when resolving an abstract.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(_IAbstract, _ConcreteA)
        self.assertIsInstance(await c.make(_IAbstract), _ConcreteA)

    async def testMakeReturnsTheInstanceRegisteredInTheScope(self) -> None:
        """
        Return the scope entry when the abstract is already stored there.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        service = _Plain()
        async with c.beginScope():
            c.instance(None, service)
            self.assertIs(await c.make(_Plain), service)

# ===========================================================================
# build()
# ===========================================================================

class TestContainerBuild(_ScopelessTestCase):

    async def testBuildPlainClassReturnsInstance(self) -> None:
        """
        Create an instance of a plain class with no constructor arguments.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertIsInstance(await c.build(_Plain), _Plain)

    async def testBuildClassWithDepAutoResolvesConstructorArg(self) -> None:
        """
        Inject an unregistered dependency into the constructor automatically.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        instance = await c.build(_NeedsPlain)
        self.assertIsInstance(instance, _NeedsPlain)
        self.assertIsInstance(instance.dep, _Plain)

    async def testBuildNonClassRaisesTypeError(self) -> None:
        """
        Raise TypeError when build() receives a non-class argument.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            await c.build(_NOT_A_CLASS)  # type: ignore[arg-type]

    async def testBuildAlwaysCreatesNewInstanceForRegisteredSingleton(
        self,
    ) -> None:
        """
        Bypass the singleton cache and create a fresh instance with build().

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.singleton(None, _Plain)
        singleton = await c.make(_Plain)
        built = await c.build(_Plain)
        self.assertIsNot(singleton, built)

# ===========================================================================
# Constructor signature resolution
# ===========================================================================

class TestContainerSignatureResolution(_ScopelessTestCase):

    async def testBoundPositionalDependencyIsResolvedFromContainer(
        self,
    ) -> None:
        """
        Resolve a positional dependency through its container binding.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        shared = _Plain()
        c.instance(None, shared)
        instance = await c.build(_NeedsPlain)
        self.assertIs(instance.dep, shared)

    async def testExplicitPositionalArgumentWinsOverAutoResolution(
        self,
    ) -> None:
        """
        Consume the supplied positional argument instead of auto-resolving.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        supplied = _Plain()
        instance = await c.build(_NeedsPlain, supplied)
        self.assertIs(instance.dep, supplied)

    async def testExplicitKeywordArgumentFeedsAPositionalParameter(
        self,
    ) -> None:
        """
        Consume a keyword argument that targets a positional parameter.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        supplied = _Plain()
        instance = await c.build(_NeedsPlain, dep=supplied)
        self.assertIs(instance.dep, supplied)

    async def testExtraArgumentsAreForwardedToTheConstructor(self) -> None:
        """
        Forward unmatched positional and keyword arguments to the constructor.

        Returns
        -------
        None
            This method does not return a value.
        """
        captured: dict[str, object] = {}

        class _Variadic:
            """Service capturing every argument it receives."""

            def __init__(
                self,
                dep: _Plain,
                *args: object,
                **kwargs: object,
            ) -> None:
                """Record the variadic arguments received."""
                captured["dep"] = dep
                captured["args"] = args
                captured["kwargs"] = kwargs

        c = _fresh()
        await c.build(_Variadic, _Plain(), "extra", flag=True)

        self.assertEqual(captured["args"], ("extra",))
        self.assertEqual(captured["kwargs"], {"flag": True})

    async def testKeywordOnlyDependencyIsAutoResolved(self) -> None:
        """
        Auto-resolve a keyword-only dependency that has no explicit value.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        instance = await c.build(_NeedsKeywordPlain)
        self.assertIsInstance(instance.dep, _Plain)

    async def testBoundKeywordOnlyDependencyIsResolvedFromContainer(
        self,
    ) -> None:
        """
        Resolve a keyword-only dependency through its container binding.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        shared = _Plain()
        c.instance(None, shared)
        instance = await c.build(_NeedsKeywordPlain)
        self.assertIs(instance.dep, shared)

    async def testExplicitKeywordOnlyArgumentWinsOverAutoResolution(
        self,
    ) -> None:
        """
        Consume the supplied keyword-only argument instead of resolving it.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        supplied = _Plain()
        c.instance(None, _Plain())
        instance = await c.build(_NeedsKeywordPlain, dep=supplied)
        self.assertIs(instance.dep, supplied)

    async def testParameterDefaultIsUsedWhenNothingElseResolves(self) -> None:
        """
        Fall back to the declared default of an unbound parameter.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        instance = await c.build(_NeedsDefault)
        self.assertEqual(instance.flag, "fallback")

    async def testBuiltinParameterWithoutDefaultRaisesTypeError(self) -> None:
        """
        Raise TypeError for a builtin-typed parameter without a default.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError) as ctx:
            await c.build(_NeedsBuiltin)
        self.assertIn("built-in type", str(ctx.exception))

# ===========================================================================
# Schema arguments
# ===========================================================================

class TestContainerSchemaArguments(_ScopelessTestCase):

    def setUp(self) -> None:
        """Bind a request double so schema arguments can be validated."""
        super().setUp()
        self._container = _fresh()
        self._container.instance(Request, _StubRequest())

    async def testPositionalSchemaArgumentIsValidatedFromRequestBody(
        self,
    ) -> None:
        """
        Validate the request body into a positional schema argument.

        Returns
        -------
        None
            This method does not return a value.
        """
        instance = await self._container.build(_NeedsSchema)

        self.assertIsInstance(instance.payload, _PayloadSchema)
        self.assertEqual(instance.payload.name, _SCHEMA_NAME)

    async def testKeywordSchemaArgumentIsValidatedFromRequestBody(
        self,
    ) -> None:
        """
        Validate the request body into a keyword-only schema argument.

        Returns
        -------
        None
            This method does not return a value.
        """
        instance = await self._container.build(_NeedsKeywordSchema)

        self.assertIsInstance(instance.payload, _PayloadSchema)
        self.assertEqual(instance.payload.name, _SCHEMA_NAME)

# ===========================================================================
# Deferred providers
# ===========================================================================

class TestContainerDeferredProviders(_ScopelessTestCase):

    def setUp(self) -> None:
        """Attach a fresh container to every deferred provider double."""
        super().setUp()
        self._container = _fresh()
        self._container._deferred_providers = dict(_DEFERRED_REGISTRY)
        _AsyncDeferredProvider.reset(self._container)
        _SyncDeferredProvider.reset(self._container)
        _DependencyProvider.reset(self._container)

    def tearDown(self) -> None:
        """Detach the container from every deferred provider double."""
        _AsyncDeferredProvider.reset(None)
        _SyncDeferredProvider.reset(None)
        _DependencyProvider.reset(None)
        super().tearDown()

    async def testAliasTriggersDeferredProviderWithAsyncBoot(self) -> None:
        """
        Register and boot a deferred provider declaring an async boot hook.

        Returns
        -------
        None
            This method does not return a value.
        """
        resolved = await self._container.make(_ASYNC_ALIAS)

        self.assertIsInstance(resolved, _DeferredService)
        self.assertEqual(_AsyncDeferredProvider.register_calls, 1)
        self.assertEqual(_AsyncDeferredProvider.boot_calls, 1)

    async def testAliasTriggersDeferredProviderWithSyncBoot(self) -> None:
        """
        Register and boot a deferred provider declaring a sync boot hook.

        Returns
        -------
        None
            This method does not return a value.
        """
        resolved = await self._container.make(_SYNC_ALIAS)

        self.assertIsInstance(resolved, _DeferredService)
        self.assertEqual(_SyncDeferredProvider.boot_calls, 1)

    async def testUnknownAliasStillRaisesAfterDeferredLookup(self) -> None:
        """
        Raise ValueError when no deferred provider publishes the alias.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            await self._container.make("missing_deferred_alias")

    async def testTypesOutsideTheRegistrySkipDeferredResolution(self) -> None:
        """
        Skip deferred resolution for a type absent from the registry.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(await self._container.build(_Plain), _Plain)
        self.assertEqual(_AsyncDeferredProvider.register_calls, 0)

    async def testConstructorDependencyTriggersDeferredProvider(self) -> None:
        """
        Resolve a constructor dependency published by a deferred provider.

        Returns
        -------
        None
            This method does not return a value.
        """
        instance = await self._container.build(_NeedsDeferredDep)

        self.assertIsInstance(instance.dep, _DeferredKwService)
        self.assertEqual(_DependencyProvider.register_calls, 1)

    async def testDeferredProviderIsResolvedOnlyOnce(self) -> None:
        """
        Run a deferred provider once even when its service is built twice.

        Returns
        -------
        None
            This method does not return a value.
        """
        await self._container.build(_NeedsDeferredDep)
        await self._container.build(_NeedsDeferredDep)

        self.assertEqual(_DependencyProvider.register_calls, 1)

    async def testConcurrentResolutionsRunTheDeferredProviderOnce(
        self,
    ) -> None:
        """
        Bootstrap a deferred provider once under concurrent first resolution.

        Registering a provider spans several await points, so without
        serialisation every racing task would run ``register()`` again and the
        duplicate binding would raise.

        Returns
        -------
        None
            This method does not return a value.
        """
        results = await asyncio.gather(
            *(self._container.build(_NeedsDeferredDep)
              for _ in range(_CONCURRENT_TASKS)),
        )

        self.assertEqual(len(results), _CONCURRENT_TASKS)
        self.assertEqual(_DependencyProvider.register_calls, 1)

# ===========================================================================
# Concurrency guarantees
# ===========================================================================

class TestContainerConcurrentResolution(_ScopelessTestCase):

    def setUp(self) -> None:
        """Bind a suspending request double and reset the build counters."""
        super().setUp()
        self._container = _fresh()
        self._container.instance(Request, _SlowRequest())
        _SuspendingSingleton.constructions = 0
        _SuspendingScoped.constructions = 0

    async def testConcurrentSingletonResolutionsShareOneInstance(self) -> None:
        """
        Build a singleton once when several tasks resolve it simultaneously.

        The construction path suspends while validating the request body, so
        the singleton cache is still empty when every task reaches it.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._container.singleton(None, _SuspendingSingleton)

        results = await asyncio.gather(
            *(self._container.make(_SuspendingSingleton)
              for _ in range(_CONCURRENT_TASKS)),
        )

        self.assertEqual(len({id(item) for item in results}), 1)
        self.assertEqual(_SuspendingSingleton.constructions, 1)

    async def testConcurrentScopedResolutionsShareOneInstance(self) -> None:
        """
        Build a scoped service once when several tasks share one scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._container.scoped(None, _SuspendingScoped)

        async with self._container.beginScope():
            results = await asyncio.gather(
                *(self._container.make(_SuspendingScoped)
                  for _ in range(_CONCURRENT_TASKS)),
            )

        self.assertEqual(len({id(item) for item in results}), 1)
        self.assertEqual(_SuspendingScoped.constructions, 1)

    async def testSeparateScopesStillGetTheirOwnInstance(self) -> None:
        """
        Keep one instance per scope even though the lock is shared by key.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._container.scoped(None, _SuspendingScoped)

        async def resolve() -> object:
            async with self._container.beginScope():
                return await self._container.make(_SuspendingScoped)

        first, second = await asyncio.gather(resolve(), resolve())

        self.assertIsNot(first, second)
        self.assertEqual(_SuspendingScoped.constructions, 2)

    async def testSingletonCycleRaisesInsteadOfDeadlocking(self) -> None:
        """
        Report a cycle between singletons instead of blocking on the lock.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.singleton(None, _CircA)
        c.singleton(None, _CircB)

        with self.assertRaises(CircularDependencyException):
            await asyncio.wait_for(c.make(_CircB), timeout=_CYCLE_TIMEOUT)

    async def testScopedCycleRaisesInsteadOfDeadlocking(self) -> None:
        """
        Report a cycle between scoped services instead of blocking.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.scoped(None, _CircA)
        c.scoped(None, _CircB)

        async with c.beginScope():
            with self.assertRaises(CircularDependencyException):
                await asyncio.wait_for(c.make(_CircB), timeout=_CYCLE_TIMEOUT)

    async def testNestedSingletonChainResolvesWithoutDeadlock(self) -> None:
        """
        Resolve a chain of singletons that depend on one another.

        Each level takes the creation lock of a different contract, so the
        nested construction must complete instead of blocking.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.singleton(None, _Plain)
        c.singleton(None, _NeedsPlain)

        instance = await asyncio.wait_for(
            c.make(_NeedsPlain), timeout=_CYCLE_TIMEOUT,
        )

        self.assertIs(instance.dep, await c.make(_Plain))

class TestContainerCreationLocks(_ScopelessTestCase):

    async def testLockIsReusedForTheSameKeyOnTheSameLoop(self) -> None:
        """
        Return the identical lock for repeated requests on one loop.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()

        self.assertIs(
            c._Container__creationLock(_Plain),
            c._Container__creationLock(_Plain),
        )

    def testLockIsRebuiltForADifferentEventLoop(self) -> None:
        """
        Replace the cached lock when the running loop is a different one.

        An ``asyncio.Lock`` binds to the loop that first awaits it, so reusing
        it from another loop would fail.

        Returns
        -------
        None
            This method does not return a value.
        """
        first, second = _locks_from_two_loops(_fresh())

        self.assertIsNotNone(first)
        self.assertIsNot(first, second)

class TestContainerThreadSafety(_ScopelessTestCase):

    def testSingletonCreationIsThreadSafe(self) -> None:
        """
        Return one instance when many OS threads construct the same subclass.

        Returns
        -------
        None
            This method does not return a value.
        """
        class _Threaded(Container):
            pass

        barrier = threading.Barrier(_CONCURRENT_THREADS)
        seen: list[Container] = []
        guard = threading.Lock()

        def build() -> None:
            barrier.wait()
            instance = _Threaded()
            with guard:
                seen.append(instance)

        threads = [
            threading.Thread(target=build)
            for _ in range(_CONCURRENT_THREADS)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        try:
            self.assertEqual(len(seen), _CONCURRENT_THREADS)
            self.assertEqual(len({id(item) for item in seen}), 1)
        finally:
            Container._instances.pop(_Threaded, None)

# ===========================================================================
# invoke()
# ===========================================================================

class TestContainerInvoke(_ScopelessTestCase):

    async def testInvokeSyncFunctionReturnsResult(self) -> None:
        """
        Execute a plain synchronous function and return its result.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertEqual(await c.invoke(_fn_no_dep), "ok")

    async def testInvokeAsyncFunctionReturnsResult(self) -> None:
        """
        Await a dependency-free coroutine function and return its result.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertEqual(await c.invoke(_afn_no_dep), "async_ok")

    async def testInvokeFunctionInjectedDependency(self) -> None:
        """
        Inject a dependency into a synchronous function and return it.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertIsInstance(await c.invoke(_fn_with_dep), _Plain)

    async def testInvokeAsyncFunctionInjectedDependency(self) -> None:
        """
        Inject a dependency into a coroutine function and await the result.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertIsInstance(await c.invoke(_afn_with_dep), _Plain)

    async def testInvokeClassRaisesTypeError(self) -> None:
        """
        Raise TypeError when invoke() receives a class type.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            await c.invoke(_Plain)  # type: ignore[arg-type]

    async def testInvokeNonCallableRaisesTypeError(self) -> None:
        """
        Raise TypeError when invoke() receives a non-callable object.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            await c.invoke(_NOT_A_CLASS)  # type: ignore[arg-type]

# ===========================================================================
# call()
# ===========================================================================

class TestContainerCall(_ScopelessTestCase):

    async def testCallMethodReturnsCorrectResult(self) -> None:
        """
        Dispatch to the named method and return its value.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertEqual(await c.call(_Host(), "greet"), "hello")

    async def testCallMissingMethodRaisesAttributeError(self) -> None:
        """
        Raise AttributeError when the method does not exist on the instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(AttributeError):
            await c.call(_Host(), "nonexistent_method")

    async def testCallNonCallableAttributeRaisesTypeError(self) -> None:
        """
        Raise TypeError when the named attribute is not callable.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        with self.assertRaises(TypeError):
            await c.call(_Host(), "non_callable")

    async def testCallMethodWithInjectedDependency(self) -> None:
        """
        Inject a declared dependency into the dispatched method.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        self.assertIsInstance(await c.call(_Host(), "echo"), _Plain)

# ===========================================================================
# Circular dependency detection
# ===========================================================================

class TestContainerCircularDependency(_ScopelessTestCase):

    async def testCircularDependencyRaisesException(self) -> None:
        """
        Raise CircularDependencyException for mutually dependent classes.

        The pair _CircA to _CircB to _CircA forms a cycle the container must
        detect while resolving constructor dependencies.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _CircA)
        c.transient(None, _CircB)
        with self.assertRaises(CircularDependencyException):
            await c.make(_CircB)

    async def testResolutionStackIsRestoredAfterAFailure(self) -> None:
        """
        Restore the resolution stack after a circular dependency failure.

        Validates that a later, acyclic resolution still succeeds once the
        failing one has unwound.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.transient(None, _CircA)
        c.transient(None, _CircB)
        with self.assertRaises(CircularDependencyException):
            await c.make(_CircB)
        self.assertIsInstance(await c.make(_Plain), _Plain)

# ===========================================================================
# Defensive resolution branches
# ===========================================================================

class TestContainerLifetimeResolution(_ScopelessTestCase):

    async def testSingletonBindingReturnsTheInstanceAlreadyCached(
        self,
    ) -> None:
        """
        Return the cached singleton without taking the creation lock.

        Validates the fast check that runs before the lock is acquired.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        cached = _Plain()
        c.instance(None, cached)
        binding = Binding(
            contract=_Plain,
            concrete=_Plain,
            lifetime=Lifetime.SINGLETON,
        )

        self.assertIs(await c._Container__resolve(binding), cached)

    async def testScopedBindingReturnsTheInstanceCachedInTheScope(
        self,
    ) -> None:
        """
        Return the cached scope entry when resolving a scoped binding.

        Validates the defensive scope lookup performed while a binding with
        SCOPED lifetime is resolved.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        binding = Binding(
            contract=_Plain,
            concrete=_Plain,
            lifetime=Lifetime.SCOPED,
        )
        cached = _Plain()
        async with c.beginScope() as scope:
            scope[_Plain] = cached
            resolved = await c._Container__resolve(binding)
        self.assertIs(resolved, cached)

    async def testUnknownLifetimeResolvesToNone(self) -> None:
        """
        Return None for a binding whose lifetime is outside the enum.

        Validates the defensive fallback that closes the lifetime dispatch.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        resolved = await c._Container__resolve(_UnknownLifetimeBinding())
        self.assertIsNone(resolved)

class TestContainerArgumentResolution(_ScopelessTestCase):

    async def testUnresolvedNonBuiltinArgumentRaisesTypeError(self) -> None:
        """
        Raise TypeError for an unresolved argument outside builtins.

        Validates the branch asking the caller to register the dependency or
        declare a default value.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        argument = Argument(
            name="dep",
            resolved=False,
            module_name=_Plain.__module__,
            class_name=_Plain.__name__,
            type=_Plain,
            full_class_path=f"{_Plain.__module__}.{_Plain.__name__}",
        )
        with self.assertRaises(TypeError) as ctx:
            await c._Container__resolveArgument(argument)
        self.assertIn("register the dependency", str(ctx.exception))

# ===========================================================================
# Scope management: beginScope() / getCurrentScope()
# ===========================================================================

class TestContainerScopeManagement(_ScopelessTestCase):

    def testBeginScopeReturnsScopeManager(self) -> None:
        """
        Return a ScopeManager instance from beginScope().

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_fresh().beginScope(), ScopeManager)

    def testGetCurrentScopeReturnsNoneOutsideScope(self) -> None:
        """
        Return None from getCurrentScope() when no scope is active.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsNone(_fresh().getCurrentScope())

    async def testGetCurrentScopeReturnsActiveObjectInsideScope(self) -> None:
        """
        Return the active scope manager while inside an open scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        async with c.beginScope() as nested:
            self.assertIs(c.getCurrentScope(), nested)

    async def testGetCurrentScopeDropsTheScopeAfterItExits(self) -> None:
        """
        Drop the nested scope from the context once its block exits.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        async with c.beginScope() as nested:
            self.assertIs(c.getCurrentScope(), nested)
        self.assertIsNone(c.getCurrentScope())

    async def testScopedInstanceIsNotVisibleOutsideScope(self) -> None:
        """
        Clear the scoped instance once the surrounding scope block exits.

        The scoped binding survives globally, but with no owning scope the
        container must raise RuntimeError again.

        Returns
        -------
        None
            This method does not return a value.
        """
        c = _fresh()
        c.scoped(None, _Plain)
        async with c.beginScope():
            self.assertIsInstance(await c.make(_Plain), _Plain)
        with self.assertRaises(RuntimeError):
            await c.make(_Plain)
