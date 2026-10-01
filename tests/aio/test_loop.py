import asyncio
import concurrent.futures
import sys
import threading
import types
from typing import TYPE_CHECKING
from unittest.mock import patch
from orionis.aio.loop import Loop
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Callable

# Seconds slept by the helper coroutine that is meant to stay pending.
_SLEEP_SECONDS = 3600

def call_off_loop[T](target: Callable[..., T], *args: object) -> T:
    """Run a callable in a worker thread without an active event loop.

    Parameters
    ----------
    target : Callable[..., T]
        Callable to execute in the worker thread.
    *args : object
        Positional arguments passed to ``target``.

    Returns
    -------
    T
        Value returned by ``target``.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(target, *args).result()

def new_loop_probe(**overrides: object) -> type[Loop]:
    """Build an isolated ``Loop`` subclass with independent class state.

    Parameters
    ----------
    **overrides : object
        Class attributes to replace on the probe.

    Returns
    -------
    type[Loop]
        A ``Loop`` subclass with isolated state.
    """

    class LoopProbe(Loop):
        """Loop manager whose shared state never reaches the real class."""

        _IS_WIN32 = False
        _uvloop_checked = False
        _uvloop_factory = None
        _loop_lock = threading.Lock()
        _loop_factory_resolved = False
        _loop_factory_cached = None
        _loop_local = threading.local()
        _sync_executor = None
        _sync_executor_lock = threading.Lock()

    for attribute, value in overrides.items():
        setattr(LoopProbe, attribute, value)
    return LoopProbe

def new_fake_uvloop_module() -> types.ModuleType:
    """Build a stand-in ``uvloop`` module exposing a loop factory.

    Returns
    -------
    types.ModuleType
        Module whose ``new_event_loop`` attribute uses asyncio's factory.
    """
    module = types.ModuleType("uvloop")
    module.__dict__["new_event_loop"] = asyncio.new_event_loop
    return module

async def coroutine_returning(value: object) -> object:
    """Return a value from an asynchronous context.

    Parameters
    ----------
    value : object
        Value to return.

    Returns
    -------
    object
        The received value.
    """
    return value

async def coroutine_joining(first: str, second: str) -> str:
    """Join two fragments from an asynchronous context.

    Parameters
    ----------
    first : str
        First fragment.
    second : str
        Second fragment.

    Returns
    -------
    str
        Both fragments joined by a hyphen.
    """
    return f"{first}-{second}"

async def coroutine_raising(exception: type[Exception], message: str) -> None:
    """Raise an exception from an asynchronous context.

    Parameters
    ----------
    exception : type[Exception]
        Exception class to raise.
    message : str
        Message supplied to the exception.

    Raises
    ------
    Exception
        Always raises an instance of ``exception``.
    """
    raise exception(message)

async def coroutine_interrupted() -> None:
    """Emulate a ``Ctrl+C`` received while the entry point is running.

    Raises
    ------
    KeyboardInterrupt
        Always raises the simulated user interruption.
    """
    raise KeyboardInterrupt

async def coroutine_sleeping() -> None:
    """Wait long enough for the caller to cancel the resulting task.

    Notes
    -----
    The long delay keeps the task pending until it is cancelled.
    """
    await asyncio.sleep(_SLEEP_SECONDS)

def sync_returning(value: object) -> object:
    """Return a value from a synchronous context.

    Parameters
    ----------
    value : object
        Value to return.

    Returns
    -------
    object
        The received value.
    """
    return value

def sync_joining(first: str, second: str) -> str:
    """Join two fragments from a synchronous context.

    Parameters
    ----------
    first : str
        First fragment.
    second : str
        Second fragment.

    Returns
    -------
    str
        Both fragments joined by a hyphen.
    """
    return f"{first}-{second}"

def sync_raising(exception: type[Exception], message: str) -> None:
    """Raise an exception from a synchronous context.

    Parameters
    ----------
    exception : type[Exception]
        Exception class to raise.
    message : str
        Message supplied to the exception.

    Raises
    ------
    Exception
        Always raises an instance of ``exception``.
    """
    raise exception(message)

def sync_returning_awaitable(value: object) -> object:
    """Return a coroutine instead of an already computed value.

    Parameters
    ----------
    value : object
        Value forwarded to the coroutine.

    Returns
    -------
    object
        Coroutine that resolves to ``value``.
    """
    return coroutine_returning(value)

def acquire_thread_loop() -> asyncio.AbstractEventLoop:
    """Acquire the loop provided for the calling thread.

    Returns
    -------
    asyncio.AbstractEventLoop
        Event loop provided by ``Loop``.
    """
    return Loop.getEventLoop()

def acquire_thread_loop_twice() -> tuple[
    asyncio.AbstractEventLoop,
    asyncio.AbstractEventLoop,
]:
    """Acquire the same thread's loop twice.

    Returns
    -------
    tuple[asyncio.AbstractEventLoop, asyncio.AbstractEventLoop]
        The two loop references.
    """
    return Loop.getEventLoop(), Loop.getEventLoop()

def replace_closed_thread_loop() -> tuple[
    asyncio.AbstractEventLoop,
    asyncio.AbstractEventLoop,
]:
    """Close the cached loop and acquire its replacement.

    Returns
    -------
    tuple[asyncio.AbstractEventLoop, asyncio.AbstractEventLoop]
        The closed loop and its replacement.
    """
    first = Loop.getEventLoop()
    first.close()
    return first, Loop.getEventLoop()

def acquire_probe_loop(
    probe: type[Loop],
) -> tuple[asyncio.AbstractEventLoop, bool]:
    """Acquire a probe loop and report whether it was cached.

    Parameters
    ----------
    probe : type[Loop]
        Isolated loop manager to query.

    Returns
    -------
    tuple[asyncio.AbstractEventLoop, bool]
        The acquired loop and whether the thread-local cache holds it.
    """
    loop = probe.getEventLoop()
    return loop, probe._loop_local.__dict__.get("loop") is loop

def context_without_pending_tasks() -> tuple[asyncio.AbstractEventLoop, bool]:
    """Use a loop context without creating pending tasks.

    Returns
    -------
    tuple[asyncio.AbstractEventLoop, bool]
        The managed loop and whether it remained open inside the context.
    """
    with Loop.eventLoopContext() as loop:
        open_inside = not loop.is_closed()
    return loop, open_inside

def context_cancelling_pending_task() -> asyncio.Task[None]:
    """Create a task that the managed context cancels on exit.

    Returns
    -------
    asyncio.Task[None]
        The cancelled task.
    """
    with Loop.eventLoopContext() as loop:
        task = loop.create_task(coroutine_sleeping())
    loop.close()
    return task

def context_with_a_closed_loop() -> bool:
    """Close a managed loop inside its context.

    Returns
    -------
    bool
        Whether the context exits with the loop closed.
    """
    with Loop.eventLoopContext() as loop:
        task = loop.create_task(coroutine_sleeping())
        loop.run_until_complete(asyncio.sleep(0))
        task._log_destroy_pending = False
        loop.close()
    return loop.is_closed()

class _MarkingLock:
    """Lock double publishing a value the moment it is acquired."""

    __slots__ = ("attribute", "entries", "owner", "value")

    def __init__(self, attribute: str, value: object) -> None:
        """Store the attribute and value published on acquisition.

        Parameters
        ----------
        attribute : str
            Owner attribute to update.
        value : object
            Value published when the lock is acquired.
        """
        self.attribute = attribute
        self.value = value
        self.owner: object = None
        self.entries = 0

    def bindTo(self, owner: object) -> None:
        """Bind the lock to the object whose state it publishes.

        Parameters
        ----------
        owner : object
            Object receiving the published attribute.
        """
        self.owner = owner

    def __enter__(self) -> None:
        """Publish the value as if a competing thread had produced it.

        Returns
        -------
        None
            Updates the owner's configured attribute.
        """
        self.entries += 1
        setattr(self.owner, self.attribute, self.value)

    def __exit__(self, *_exc_info: object) -> bool:
        """Exit the lock context without suppressing exceptions.

        Parameters
        ----------
        *_exc_info : object
            Exception details supplied by the context manager protocol.

        Returns
        -------
        bool
            Always returns ``False``.
        """
        return False

class TestRunningLoopDetection(TestCase):

    def testReturnsTheLoopDrivingTheCallingThread(self) -> None:
        """
        Return the loop currently running in the calling thread.

        Validates that the helper reports exactly the object handed out by
        ``asyncio.get_running_loop``.

        Returns
        -------
        None
            Asserts that the running loop is returned unchanged.
        """
        self.assertIs(Loop._getRunningLoop(), asyncio.get_running_loop())

    def testReturnsNoneInAThreadWithoutALoop(self) -> None:
        """
        Return None when the calling thread has no running loop.

        Validates that the ``RuntimeError`` raised by asyncio is translated
        into a plain ``None`` result.

        Returns
        -------
        None
            Asserts that a thread without a loop produces ``None``.
        """
        self.assertIsNone(call_off_loop(Loop._getRunningLoop))

class TestLoopRunningFlag(TestCase):

    def testReportsTheLoopDrivingTheCallingThread(self) -> None:
        """
        Report an active loop while the test runner drives the call.

        Validates the boolean shortcut used by callers that only need to
        know whether they are inside a loop.

        Returns
        -------
        None
            Asserts that the active loop is reported.
        """
        self.assertTrue(Loop.isLoopRunning())

    def testReportsNoLoopInAPlainThread(self) -> None:
        """
        Report no active loop from a thread that never started one.

        Validates that the flag mirrors the absence of a running loop
        instead of the mere existence of a cached one.

        Returns
        -------
        None
            Asserts that a plain thread has no active loop.
        """
        self.assertFalse(call_off_loop(Loop.isLoopRunning))

class TestUvloopDetectionWhenImportable(TestCase):
    """Detection performed while a ``uvloop`` module can be imported."""

    def setUp(self) -> None:
        """Publish a stand-in module in the import cache.

        Returns
        -------
        None
            Installs the fake module for this test.
        """
        self.previous = sys.modules.get("uvloop")
        self.module = new_fake_uvloop_module()
        sys.modules["uvloop"] = self.module

    def tearDown(self) -> None:
        """Restore the original import cache contents.

        Returns
        -------
        None
            Restores or removes the fake module.
        """
        if self.previous is None:
            sys.modules.pop("uvloop", None)
        else:
            sys.modules["uvloop"] = self.previous

    def testCachesTheUvloopFactoryOutsideWindows(self) -> None:
        """
        Adopt the uvloop factory when the module can be imported.

        Validates that the detected callable is returned and cached so the
        import is never repeated.

        Returns
        -------
        None
            Asserts that the detected factory is cached.
        """
        probe = new_loop_probe()
        detected = probe._detectUvloop()
        self.assertIs(detected, self.module.new_event_loop)
        self.assertIs(probe._uvloop_factory, detected)
        self.assertTrue(probe._uvloop_checked)

    def testIgnoresUvloopOnWindows(self) -> None:
        """
        Skip uvloop on Windows even when the module is importable.

        Validates that the platform guard runs before the import so an
        unsupported loop implementation is never selected.

        Returns
        -------
        None
            Asserts that Windows skips the optional factory.
        """
        probe = new_loop_probe(_IS_WIN32=True)
        self.assertIsNone(probe._detectUvloop())
        self.assertTrue(probe._uvloop_checked)

class TestUvloopDetectionWhenMissing(TestCase):
    """Detection performed while the ``uvloop`` import is blocked."""

    def setUp(self) -> None:
        """Block the ``uvloop`` import for the test.

        Returns
        -------
        None
            Marks the optional module as unavailable.
        """
        self.previous = sys.modules.get("uvloop")
        sys.modules["uvloop"] = None  # type: ignore[assignment]

    def tearDown(self) -> None:
        """Restore the original import cache contents.

        Returns
        -------
        None
            Restores or removes the unavailable-module marker.
        """
        if self.previous is None:
            sys.modules.pop("uvloop", None)
        else:
            sys.modules["uvloop"] = self.previous

    def testReturnsNoFactoryWhenTheImportFails(self) -> None:
        """
        Return None when uvloop cannot be imported.

        Validates that the ``ImportError`` is swallowed and the detection
        is still marked as completed.

        Returns
        -------
        None
            Asserts that failed detection is cached as unavailable.
        """
        probe = new_loop_probe()
        self.assertIsNone(probe._detectUvloop())
        self.assertIsNone(probe._uvloop_factory)
        self.assertTrue(probe._uvloop_checked)

class TestUvloopDetectionCaching(TestCase):

    def testReturnsTheCachedFactoryWithoutAcquiringTheLock(self) -> None:
        """
        Return the cached factory once the detection already ran.

        Validates that the guarded fast path answers before the lock is
        acquired, keeping repeated calls free of contention.

        Returns
        -------
        None
            Asserts that the cached result avoids lock acquisition.
        """
        lock = _MarkingLock("_uvloop_checked", True)
        probe = new_loop_probe(
            _uvloop_checked=True,
            _uvloop_factory=asyncio.new_event_loop,
            _loop_lock=lock,
        )
        lock.bindTo(probe)
        self.assertIs(probe._detectUvloop(), asyncio.new_event_loop)
        self.assertEqual(lock.entries, 0)

    def testSkipsTheImportWhenAnotherThreadWonTheRace(self) -> None:
        """
        Skip the import when another thread completed the detection first.

        Validates the second half of the double-checked locking: the state
        is re-read inside the critical section before importing.

        Returns
        -------
        None
            Asserts that a competing result prevents another import.
        """
        lock = _MarkingLock("_uvloop_checked", True)
        probe = new_loop_probe(_loop_lock=lock)
        lock.bindTo(probe)
        self.assertIsNone(probe._detectUvloop())
        self.assertIsNone(probe._uvloop_factory)
        self.assertEqual(lock.entries, 1)

class TestLoopFactoryResolution(TestCase):

    def testAdoptsTheUvloopFactoryWhenDetected(self) -> None:
        """
        Prefer uvloop over every other loop implementation.

        Validates that a successful detection short-circuits the platform
        specific branches and is cached for later calls.

        Returns
        -------
        None
            Asserts that the detected factory becomes the cached result.
        """
        probe = new_loop_probe(
            _uvloop_checked=True,
            _uvloop_factory=asyncio.new_event_loop,
        )
        factory = probe._getLoopFactory()
        self.assertIs(factory, asyncio.new_event_loop)
        self.assertIs(probe._loop_factory_cached, factory)
        self.assertTrue(probe._loop_factory_resolved)

    def testSelectsTheProactorFactoryOnWindows(self) -> None:
        """
        Select the Proactor loop on Windows when uvloop is unavailable.

        Validates the platform branch, including the guard that tolerates
        interpreters where the Proactor loop is not exposed.

        Returns
        -------
        None
            Asserts that Windows selects its available factory.
        """
        probe = new_loop_probe(_IS_WIN32=True, _uvloop_checked=True)
        expected = getattr(asyncio, "ProactorEventLoop", None)
        self.assertIs(probe._getLoopFactory(), expected)
        self.assertTrue(probe._loop_factory_resolved)

    def testReportsNoFactoryOutsideWindowsWithoutUvloop(self) -> None:
        """
        Report no factory when neither uvloop nor Proactor applies.

        Validates that callers are told to fall back to the asyncio
        default loop implementation.

        Returns
        -------
        None
            Asserts that no optimized factory is selected.
        """
        probe = new_loop_probe(_uvloop_checked=True)
        self.assertIsNone(probe._getLoopFactory())
        self.assertTrue(probe._loop_factory_resolved)

    def testReturnsTheResolvedFactoryWithoutDetectingAgain(self) -> None:
        """
        Return the resolved factory without repeating the detection.

        Validates that the cached answer is served before any uvloop lookup
        is attempted.

        Returns
        -------
        None
            Asserts that the cached factory is returned directly.
        """
        lock = _MarkingLock("_uvloop_checked", True)
        probe = new_loop_probe(
            _loop_factory_resolved=True,
            _loop_factory_cached=asyncio.new_event_loop,
            _loop_lock=lock,
        )
        lock.bindTo(probe)
        self.assertIs(probe._getLoopFactory(), asyncio.new_event_loop)
        self.assertEqual(lock.entries, 0)

class TestLoopFactoryWithoutTheProactorLoop(TestCase):
    """Windows resolution on a runtime that hides the Proactor loop."""

    def setUp(self) -> None:
        """Hide the Proactor loop exported by asyncio.

        Returns
        -------
        None
            Removes the optional factory for this test.
        """
        self.proactor = vars(asyncio).pop("ProactorEventLoop", None)

    def tearDown(self) -> None:
        """Restore the Proactor loop exported by asyncio.

        Returns
        -------
        None
            Restores the optional factory when it was present.
        """
        if self.proactor is not None:
            vars(asyncio)["ProactorEventLoop"] = self.proactor

    def testReportsNoFactoryWhenTheProactorLoopIsMissing(self) -> None:
        """
        Report no factory when the Proactor loop is not exposed.

        Validates the guard that keeps the Windows branch working on
        runtimes where the optimised loop implementation is absent.

        Returns
        -------
        None
            Asserts that a missing Proactor factory is tolerated.
        """
        probe = new_loop_probe(_IS_WIN32=True, _uvloop_checked=True)
        self.assertIsNone(probe._getLoopFactory())
        self.assertTrue(probe._loop_factory_resolved)

class TestSyncExecutor(TestCase):

    def testCreatesTheExecutorOnceAndReusesIt(self) -> None:
        """
        Create the bridging worker lazily and reuse it afterwards.

        Validates that thread creation stays off the hot path by caching a
        single-worker pool on the class.

        Returns
        -------
        None
            Asserts that one executor is cached and reused.
        """
        probe = new_loop_probe()
        executor = probe._getSyncExecutor()
        try:
            self.assertIsInstance(
                executor, concurrent.futures.ThreadPoolExecutor,
            )
            self.assertIs(probe._getSyncExecutor(), executor)
        finally:
            executor.shutdown(wait=True)

    def testKeepsTheExecutorBuiltByAnotherThread(self) -> None:
        """
        Keep the executor published by a competing thread.

        Validates the second half of the double-checked locking: no extra
        pool is created once the critical section observes one.

        Returns
        -------
        None
            Asserts that the executor published by the competing thread wins.
        """
        winner = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        lock = _MarkingLock("_sync_executor", winner)
        probe = new_loop_probe(_sync_executor_lock=lock)
        lock.bindTo(probe)
        try:
            self.assertIs(probe._getSyncExecutor(), winner)
            self.assertEqual(lock.entries, 1)
        finally:
            winner.shutdown(wait=True)

class TestEventLoopRetrieval(TestCase):

    def testReturnsTheLoopAlreadyRunningInTheThread(self) -> None:
        """
        Return the running loop instead of the cached one.

        Validates the fast path that prevents a second loop from being
        created inside asynchronous code.

        Returns
        -------
        None
            Asserts that the current running loop is returned.
        """
        self.assertIs(Loop.getEventLoop(), asyncio.get_running_loop())

    def testCachesASingleLoopPerThread(self) -> None:
        """
        Reuse the very same loop for every call made by one thread.

        Validates that the thread-local cache avoids rebuilding a loop that
        is still usable.

        Returns
        -------
        None
            Asserts that repeated calls reuse the thread's open loop.
        """
        first, second = call_off_loop(acquire_thread_loop_twice)
        try:
            self.assertIsInstance(first, asyncio.AbstractEventLoop)
            self.assertIs(first, second)
        finally:
            first.close()

    def testBuildsADistinctLoopForEachThread(self) -> None:
        """
        Give every thread its own event loop.

        Validates the isolation guarantee that keeps a loop from being
        shared across threads.

        Returns
        -------
        None
            Asserts that distinct threads receive distinct loops.
        """
        first = call_off_loop(acquire_thread_loop)
        second = call_off_loop(acquire_thread_loop)
        try:
            self.assertIsNot(first, second)
        finally:
            first.close()
            second.close()

    def testReplacesTheCachedLoopOnceItIsClosed(self) -> None:
        """
        Replace the cached loop when it has already been closed.

        Validates that a stale entry never leaks back to the caller.

        Returns
        -------
        None
            Asserts that a closed cached loop is replaced.
        """
        closed, replacement = call_off_loop(replace_closed_thread_loop)
        try:
            self.assertIsNot(replacement, closed)
            self.assertTrue(closed.is_closed())
            self.assertFalse(replacement.is_closed())
        finally:
            replacement.close()

    def testFallsBackToTheStandardLoopWhenNoFactoryIsResolved(self) -> None:
        """
        Build the loop with asyncio itself when no factory is available.

        Validates the fallback branch taken on platforms where neither
        uvloop nor the Proactor loop can be used.

        Returns
        -------
        None
            Asserts that asyncio creates and caches the fallback loop.
        """
        probe = new_loop_probe(
            _loop_factory_resolved=True,
            _loop_factory_cached=None,
        )
        loop, cached = call_off_loop(acquire_probe_loop, probe)
        try:
            self.assertIsInstance(loop, asyncio.AbstractEventLoop)
            self.assertTrue(cached)
        finally:
            loop.close()

class TestRunEntryPoint(TestCase):

    def testRunsTheCoroutineAndReturnsItsValue(self) -> None:
        """
        Drive the coroutine to completion and surface its result.

        Validates the nominal entry-point usage from a thread with no
        running loop.

        Returns
        -------
        None
            Asserts that the coroutine result is returned from the worker.
        """
        self.assertEqual(call_off_loop(Loop.run, coroutine_returning(42)), 42)

    def testRejectsAnythingThatIsNotACoroutineObject(self) -> None:
        """
        Reject arguments that are not coroutine objects.

        Validates that both a coroutine function and a plain value are
        refused before any loop is created.

        Returns
        -------
        None
            Asserts that non-coroutine inputs raise ``TypeError``.
        """
        with self.assertRaises(TypeError):
            Loop.run(coroutine_returning)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Loop.run(42)  # type: ignore[arg-type]

    def testReturnsZeroWhenTheCoroutineIsInterrupted(self) -> None:
        """
        Return zero when the coroutine is interrupted by the user.

        Validates that ``KeyboardInterrupt`` becomes a clean exit status
        instead of an unhandled exception.

        Returns
        -------
        None
            Asserts that interruption produces the zero exit status.
        """
        self.assertEqual(call_off_loop(Loop.run, coroutine_interrupted()), 0)

    def testPropagatesExceptionsRaisedByTheCoroutine(self) -> None:
        """
        Propagate any error other than the user interruption.

        Validates that application failures are not masked by the entry
        point wrapper.

        Returns
        -------
        None
            Asserts that the coroutine's exception reaches the caller.
        """
        with self.assertRaises(ValueError):
            call_off_loop(Loop.run, coroutine_raising(ValueError, "boom"))

    def testRefusesToStartASecondLoopInTheSameThread(self) -> None:
        """
        Refuse to start a loop where another one is already running.

        Validates the documented failure mode, including that no runner is
        opened and the coroutine stays the caller's to close.

        Returns
        -------
        None
            Asserts that a second loop is rejected and closes the coroutine.
        """
        self.assertTrue(Loop.isLoopRunning())
        coro = coroutine_returning("never started")
        try:
            with (
                patch.object(asyncio, "Runner") as runner,
                patch.object(asyncio, "run") as run,
            ):
                with self.assertRaises(RuntimeError):
                    Loop.run(coro)
                runner.assert_not_called()
                run.assert_not_called()
        finally:
            coro.close()

class TestRunWithoutAnOptimalFactory(TestCase):
    """Entry point exercised while no optimal loop factory is resolved."""

    def setUp(self) -> None:
        """Force the resolution cache to report no optimal factory.

        Returns
        -------
        None
            Sets the shared factory cache to its fallback state.
        """
        self.resolved = Loop._loop_factory_resolved
        self.cached = Loop._loop_factory_cached
        Loop._loop_factory_resolved = True
        Loop._loop_factory_cached = None

    def tearDown(self) -> None:
        """Restore the resolution cache shared by the process.

        Returns
        -------
        None
            Restores both cached factory values.
        """
        Loop._loop_factory_resolved = self.resolved
        Loop._loop_factory_cached = self.cached

    def testFallsBackToTheStandardAsyncioRunner(self) -> None:
        """
        Run the coroutine with ``asyncio.run`` when no factory exists.

        Validates the fallback branch used on platforms without uvloop or
        the Proactor loop.

        Returns
        -------
        None
            Asserts that the stdlib runner returns the coroutine result.
        """
        result = call_off_loop(Loop.run, coroutine_returning("stdlib"))
        self.assertEqual(result, "stdlib")

class TestExecuteBridge(TestCase):

    async def testOffloadsSynchronousCallablesToTheExecutor(self) -> None:
        """
        Run a blocking callable outside the loop thread.

        Validates that the returned value reaches the awaiting coroutine
        untouched.

        Returns
        -------
        None
            Asserts that the synchronous result reaches the caller.
        """
        self.assertEqual(await Loop.execute(sync_returning, 7), 7)

    async def testAwaitsCoroutineFunctionsDirectly(self) -> None:
        """
        Await a coroutine function without using the executor.

        Validates that asynchronous callables keep running on the loop
        that invoked them.

        Returns
        -------
        None
            Asserts that the coroutine result is awaited directly.
        """
        result = await Loop.execute(coroutine_returning, "hello")
        self.assertEqual(result, "hello")

    async def testForwardsKeywordArgumentsToSynchronousCallables(self) -> None:
        """
        Forward keyword arguments to the blocking callable.

        Validates the partial application performed before handing the
        work over to the executor.

        Returns
        -------
        None
            Asserts that keyword arguments reach the synchronous callable.
        """
        result = await Loop.execute(sync_joining, first="a", second="b")
        self.assertEqual(result, "a-b")

    async def testForwardsKeywordArgumentsToCoroutineFunctions(self) -> None:
        """
        Forward keyword arguments to the asynchronous callable.

        Validates that the direct await path preserves the full calling
        convention.

        Returns
        -------
        None
            Asserts that keyword arguments reach the coroutine function.
        """
        result = await Loop.execute(coroutine_joining, first="a", second="b")
        self.assertEqual(result, "a-b")

    async def testAwaitsTheAwaitableReturnedByASynchronousCallable(self) -> None:
        """
        Await the awaitable produced by a blocking callable.

        Validates that a factory returning a coroutine is resolved instead
        of being handed back to the caller.

        Returns
        -------
        None
            Asserts that a returned awaitable is awaited.
        """
        self.assertEqual(await Loop.execute(sync_returning_awaitable, 3), 3)

    async def testRejectsObjectsThatAreNotCallable(self) -> None:
        """
        Reject arguments that cannot be invoked.

        Validates that the guard runs before any scheduling attempt.

        Returns
        -------
        None
            Asserts that non-callable inputs raise ``TypeError``.
        """
        with self.assertRaises(TypeError):
            await Loop.execute(42)  # type: ignore[arg-type]

    async def testPropagatesExceptionsRaisedInTheExecutor(self) -> None:
        """
        Propagate the failure of a blocking callable.

        Validates that errors crossing the thread boundary are not
        swallowed by the executor future.

        Returns
        -------
        None
            Asserts that executor failures reach the awaiting caller.
        """
        with self.assertRaises(ValueError):
            await Loop.execute(sync_raising, ValueError, "boom")

    async def testPropagatesExceptionsRaisedByCoroutineFunctions(self) -> None:
        """
        Propagate the failure of an asynchronous callable.

        Validates that the direct await path re-raises the original error.

        Returns
        -------
        None
            Asserts that coroutine failures reach the awaiting caller.
        """
        with self.assertRaises(RuntimeError):
            await Loop.execute(coroutine_raising, RuntimeError, "boom")

class TestEventLoopContextManager(TestCase):

    def testProvidesAnOpenLoopAndLeavesItUsable(self) -> None:
        """
        Hand out a usable loop and keep it open after the block.

        Validates that a context without pending work performs no cleanup
        and never closes the loop it borrowed.

        Returns
        -------
        None
            Asserts that the borrowed loop remains open after the context.
        """
        loop, open_inside = call_off_loop(context_without_pending_tasks)
        try:
            self.assertTrue(open_inside)
            self.assertFalse(loop.is_closed())
        finally:
            loop.close()

    def testCancelsThePendingTasksOnExit(self) -> None:
        """
        Cancel and drain the tasks still pending when the block ends.

        Validates the cooperative cleanup that prevents orphan tasks from
        outliving the context.

        Returns
        -------
        None
            Asserts that the pending task is cancelled on context exit.
        """
        task = call_off_loop(context_cancelling_pending_task)
        self.assertTrue(task.cancelled())

    def testToleratesALoopClosedInsideTheBlock(self) -> None:
        """
        Leave the context silently when the loop was closed inside it.

        Validates that the cleanup never lets a ``RuntimeError`` escape the
        ``finally`` block.

        Returns
        -------
        None
            Asserts that closing the loop inside the context is tolerated.
        """
        self.assertTrue(call_off_loop(context_with_a_closed_loop))

    def testSkipsTheCleanupWhileTheLoopIsRunning(self) -> None:
        """
        Skip the cleanup when the borrowed loop is still running.

        Validates that a context opened inside asynchronous code never
        cancels the tasks driving the caller.

        Returns
        -------
        None
            Asserts that the active caller loop remains open.
        """
        running = asyncio.get_running_loop()
        with Loop.eventLoopContext() as loop:
            self.assertIs(loop, running)
        self.assertFalse(running.is_closed())

class TestTaskCreation(TestCase):

    async def testSchedulesTheCoroutineAsATask(self) -> None:
        """
        Schedule the coroutine on the running loop.

        Validates that the returned object is a task that resolves to the
        coroutine result.

        Returns
        -------
        None
            Asserts that the scheduled task resolves to the coroutine value.
        """
        task = await Loop.createTask(coroutine_returning(5))
        self.assertIsInstance(task, asyncio.Task)
        self.assertEqual(await task, 5)

    async def testAppliesTheRequestedTaskName(self) -> None:
        """
        Apply the descriptive name given to the task.

        Validates that the optional name reaches the underlying asyncio
        call so tasks stay identifiable while debugging.

        Returns
        -------
        None
            Asserts that the task receives the requested name.
        """
        task = await Loop.createTask(
            coroutine_returning(None), name="orionis-task",
        )
        self.assertEqual(task.get_name(), "orionis-task")
        await task

class TestRunSyncBridge(TestCase):

    def testRunsTheCoroutineDirectlyWithoutARunningLoop(self) -> None:
        """
        Drive the coroutine in place when no loop is running.

        Validates that the synchronous bridge avoids the worker thread
        whenever the caller owns the thread.

        Returns
        -------
        None
            Asserts that the coroutine result is returned directly.
        """
        result = call_off_loop(Loop.runSync, coroutine_returning("direct"))
        self.assertEqual(result, "direct")

    def testDispatchesToTheWorkerWhileALoopIsRunning(self) -> None:
        """
        Dispatch the coroutine to the shared worker inside a live loop.

        Validates that synchronous callers can reach asynchronous code
        without deadlocking the loop that invoked them.

        Returns
        -------
        None
            Asserts that the worker returns the coroutine result.
        """
        self.assertTrue(Loop.isLoopRunning())
        self.assertEqual(Loop.runSync(coroutine_returning("bridged")), "bridged")

    def testPropagatesExceptionsRaisedByTheCoroutine(self) -> None:
        """
        Propagate coroutine failures through the synchronous bridge.

        Validates that the worker future re-raises the original error in
        the calling thread.

        Returns
        -------
        None
            Asserts that coroutine failures reach the calling thread.
        """
        self.assertTrue(Loop.isLoopRunning())
        with self.assertRaises(RuntimeError):
            Loop.runSync(coroutine_raising(RuntimeError, "boom"))
