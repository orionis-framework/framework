import asyncio
import concurrent.futures
import sys
import threading
import types
from typing import TYPE_CHECKING
from orionis.aio.loop import Loop
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Callable

# Seconds slept by the helper coroutine that is meant to stay pending.
_SLEEP_SECONDS = 3600

def call_off_loop[T](target: Callable[..., T], *args: object) -> T:
    """Run the callable in a worker thread free of any running event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(target, *args).result()

def new_loop_probe(**overrides: object) -> type[Loop]:
    """Build an isolated ``Loop`` subclass owning its own class-level state."""
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
    """Build a stand-in ``uvloop`` module exposing a loop factory."""
    module = types.ModuleType("uvloop")
    module.__dict__["new_event_loop"] = asyncio.new_event_loop
    return module

async def coroutine_returning(value: object) -> object:
    """Return the received value from an asynchronous context."""
    return value

async def coroutine_joining(first: str, second: str) -> str:
    """Join both fragments from an asynchronous context."""
    return f"{first}-{second}"

async def coroutine_raising(exception: type[Exception], message: str) -> None:
    """Raise the requested exception from an asynchronous context."""
    raise exception(message)

async def coroutine_interrupted() -> None:
    """Emulate a ``Ctrl+C`` received while the entry point is running."""
    raise KeyboardInterrupt

async def coroutine_sleeping() -> None:
    """Await long enough for the caller to cancel the resulting task."""
    await asyncio.sleep(_SLEEP_SECONDS)

def sync_returning(value: object) -> object:
    """Return the received value from a synchronous context."""
    return value

def sync_joining(first: str, second: str) -> str:
    """Join both fragments from a synchronous context."""
    return f"{first}-{second}"

def sync_raising(exception: type[Exception], message: str) -> None:
    """Raise the requested exception from a synchronous context."""
    raise exception(message)

def sync_returning_awaitable(value: object) -> object:
    """Return a coroutine object instead of an already computed value."""
    return coroutine_returning(value)

def acquire_thread_loop() -> asyncio.AbstractEventLoop:
    """Return the loop the manager provides for the calling thread."""
    return Loop.getEventLoop()

def acquire_thread_loop_twice() -> tuple[
    asyncio.AbstractEventLoop,
    asyncio.AbstractEventLoop,
]:
    """Return the loop requested twice in a row from the same thread."""
    return Loop.getEventLoop(), Loop.getEventLoop()

def replace_closed_thread_loop() -> tuple[
    asyncio.AbstractEventLoop,
    asyncio.AbstractEventLoop,
]:
    """Return the loop cached before and after closing the first one."""
    first = Loop.getEventLoop()
    first.close()
    return first, Loop.getEventLoop()

def acquire_probe_loop(
    probe: type[Loop],
) -> tuple[asyncio.AbstractEventLoop, bool]:
    """Return the loop built by the probe and whether it was cached."""
    loop = probe.getEventLoop()
    return loop, probe._loop_local.__dict__.get("loop") is loop

def context_without_pending_tasks() -> tuple[asyncio.AbstractEventLoop, bool]:
    """Return the managed loop and whether it stayed open inside the block."""
    with Loop.eventLoopContext() as loop:
        open_inside = not loop.is_closed()
    return loop, open_inside

def context_cancelling_pending_task() -> asyncio.Task[None]:
    """Return the task left pending when the managed context exits."""
    with Loop.eventLoopContext() as loop:
        task = loop.create_task(coroutine_sleeping())
    loop.close()
    return task

def context_with_a_closed_loop() -> bool:
    """Return whether the managed context tolerates a loop closed inside it."""
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
        """Store the attribute written when the lock is acquired."""
        self.attribute = attribute
        self.value = value
        self.owner: object = None
        self.entries = 0

    def bindTo(self, owner: object) -> None:
        """Attach the lock to the class whose state it must publish."""
        self.owner = owner

    def __enter__(self) -> None:
        """Emulate a competing thread that already produced the value."""
        self.entries += 1
        setattr(self.owner, self.attribute, self.value)

    def __exit__(self, *_exc_info: object) -> bool:
        """Release the lock without swallowing any exception."""
        return False

class TestRunningLoopDetection(TestCase):

    def testReturnsTheLoopDrivingTheCallingThread(self) -> None:
        """
        Return the loop currently running in the calling thread.

        Validates that the helper reports exactly the object handed out by
        ``asyncio.get_running_loop``.
        """
        self.assertIs(Loop._getRunningLoop(), asyncio.get_running_loop())

    def testReturnsNoneInAThreadWithoutALoop(self) -> None:
        """
        Return None when the calling thread has no running loop.

        Validates that the ``RuntimeError`` raised by asyncio is translated
        into a plain ``None`` result.
        """
        self.assertIsNone(call_off_loop(Loop._getRunningLoop))

class TestLoopRunningFlag(TestCase):

    def testReportsTheLoopDrivingTheCallingThread(self) -> None:
        """
        Report an active loop while the test runner drives the call.

        Validates the boolean shortcut used by callers that only need to
        know whether they are inside a loop.
        """
        self.assertTrue(Loop.isLoopRunning())

    def testReportsNoLoopInAPlainThread(self) -> None:
        """
        Report no active loop from a thread that never started one.

        Validates that the flag mirrors the absence of a running loop
        instead of the mere existence of a cached one.
        """
        self.assertFalse(call_off_loop(Loop.isLoopRunning))

class TestUvloopDetectionWhenImportable(TestCase):
    """Detection performed while a ``uvloop`` module can be imported."""

    def setUp(self) -> None:
        """Publish a stand-in ``uvloop`` module in the import cache."""
        self.previous = sys.modules.get("uvloop")
        self.module = new_fake_uvloop_module()
        sys.modules["uvloop"] = self.module

    def tearDown(self) -> None:
        """Restore the import cache to its original contents."""
        if self.previous is None:
            sys.modules.pop("uvloop", None)
        else:
            sys.modules["uvloop"] = self.previous

    def testCachesTheUvloopFactoryOutsideWindows(self) -> None:
        """
        Adopt the uvloop factory when the module can be imported.

        Validates that the detected callable is returned and cached so the
        import is never repeated.
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
        """
        probe = new_loop_probe(_IS_WIN32=True)
        self.assertIsNone(probe._detectUvloop())
        self.assertTrue(probe._uvloop_checked)

class TestUvloopDetectionWhenMissing(TestCase):
    """Detection performed while the ``uvloop`` import is blocked."""

    def setUp(self) -> None:
        """Block the ``uvloop`` import for the duration of the test."""
        self.previous = sys.modules.get("uvloop")
        sys.modules["uvloop"] = None  # type: ignore[assignment]

    def tearDown(self) -> None:
        """Restore the import cache to its original contents."""
        if self.previous is None:
            sys.modules.pop("uvloop", None)
        else:
            sys.modules["uvloop"] = self.previous

    def testReturnsNoFactoryWhenTheImportFails(self) -> None:
        """
        Return None when uvloop cannot be imported.

        Validates that the ``ImportError`` is swallowed and the detection
        is still marked as completed.
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
        """
        probe = new_loop_probe(_uvloop_checked=True)
        self.assertIsNone(probe._getLoopFactory())
        self.assertTrue(probe._loop_factory_resolved)

    def testReturnsTheResolvedFactoryWithoutDetectingAgain(self) -> None:
        """
        Return the resolved factory without repeating the detection.

        Validates that the cached answer is served before any uvloop lookup
        is attempted.
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
        """Hide the Proactor loop published by the asyncio package."""
        self.proactor = vars(asyncio).pop("ProactorEventLoop", None)

    def tearDown(self) -> None:
        """Publish the Proactor loop again for the rest of the suite."""
        if self.proactor is not None:
            vars(asyncio)["ProactorEventLoop"] = self.proactor

    def testReportsNoFactoryWhenTheProactorLoopIsMissing(self) -> None:
        """
        Report no factory when the Proactor loop is not exposed.

        Validates the guard that keeps the Windows branch working on
        runtimes where the optimised loop implementation is absent.
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
        """
        self.assertIs(Loop.getEventLoop(), asyncio.get_running_loop())

    def testCachesASingleLoopPerThread(self) -> None:
        """
        Reuse the very same loop for every call made by one thread.

        Validates that the thread-local cache avoids rebuilding a loop that
        is still usable.
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
        """
        self.assertEqual(call_off_loop(Loop.run, coroutine_returning(42)), 42)

    def testRejectsAnythingThatIsNotACoroutineObject(self) -> None:
        """
        Reject arguments that are not coroutine objects.

        Validates that both a coroutine function and a plain value are
        refused before any loop is created.
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
        """
        self.assertEqual(call_off_loop(Loop.run, coroutine_interrupted()), 0)

    def testPropagatesExceptionsRaisedByTheCoroutine(self) -> None:
        """
        Propagate any error other than the user interruption.

        Validates that application failures are not masked by the entry
        point wrapper.
        """
        with self.assertRaises(ValueError):
            call_off_loop(Loop.run, coroutine_raising(ValueError, "boom"))

    def testRefusesToStartASecondLoopInTheSameThread(self) -> None:
        """
        Refuse to start a loop where another one is already running.

        Validates the documented failure mode, including that the coroutine
        handed over is left unconsumed and stays the caller's to close.
        """
        self.assertTrue(Loop.isLoopRunning())
        coro = coroutine_returning("never started")
        try:
            with self.assertRaises(RuntimeError):
                Loop.run(coro)
        finally:
            coro.close()

class TestRunWithoutAnOptimalFactory(TestCase):
    """Entry point exercised while no optimal loop factory is resolved."""

    def setUp(self) -> None:
        """Force the resolution cache to report no optimal factory."""
        self.resolved = Loop._loop_factory_resolved
        self.cached = Loop._loop_factory_cached
        Loop._loop_factory_resolved = True
        Loop._loop_factory_cached = None

    def tearDown(self) -> None:
        """Restore the resolution cache shared by the whole process."""
        Loop._loop_factory_resolved = self.resolved
        Loop._loop_factory_cached = self.cached

    def testFallsBackToTheStandardAsyncioRunner(self) -> None:
        """
        Run the coroutine with ``asyncio.run`` when no factory exists.

        Validates the fallback branch used on platforms without uvloop or
        the Proactor loop.
        """
        result = call_off_loop(Loop.run, coroutine_returning("stdlib"))
        self.assertEqual(result, "stdlib")

class TestExecuteBridge(TestCase):

    async def testOffloadsSynchronousCallablesToTheExecutor(self) -> None:
        """
        Run a blocking callable outside the loop thread.

        Validates that the returned value reaches the awaiting coroutine
        untouched.
        """
        self.assertEqual(await Loop.execute(sync_returning, 7), 7)

    async def testAwaitsCoroutineFunctionsDirectly(self) -> None:
        """
        Await a coroutine function without using the executor.

        Validates that asynchronous callables keep running on the loop
        that invoked them.
        """
        result = await Loop.execute(coroutine_returning, "hello")
        self.assertEqual(result, "hello")

    async def testForwardsKeywordArgumentsToSynchronousCallables(self) -> None:
        """
        Forward keyword arguments to the blocking callable.

        Validates the partial application performed before handing the
        work over to the executor.
        """
        result = await Loop.execute(sync_joining, first="a", second="b")
        self.assertEqual(result, "a-b")

    async def testForwardsKeywordArgumentsToCoroutineFunctions(self) -> None:
        """
        Forward keyword arguments to the asynchronous callable.

        Validates that the direct await path preserves the full calling
        convention.
        """
        result = await Loop.execute(coroutine_joining, first="a", second="b")
        self.assertEqual(result, "a-b")

    async def testAwaitsTheAwaitableReturnedByASynchronousCallable(self) -> None:
        """
        Await the awaitable produced by a blocking callable.

        Validates that a factory returning a coroutine is resolved instead
        of being handed back to the caller.
        """
        self.assertEqual(await Loop.execute(sync_returning_awaitable, 3), 3)

    async def testRejectsObjectsThatAreNotCallable(self) -> None:
        """
        Reject arguments that cannot be invoked.

        Validates that the guard runs before any scheduling attempt.
        """
        with self.assertRaises(TypeError):
            await Loop.execute(42)  # type: ignore[arg-type]

    async def testPropagatesExceptionsRaisedInTheExecutor(self) -> None:
        """
        Propagate the failure of a blocking callable.

        Validates that errors crossing the thread boundary are not
        swallowed by the executor future.
        """
        with self.assertRaises(ValueError):
            await Loop.execute(sync_raising, ValueError, "boom")

    async def testPropagatesExceptionsRaisedByCoroutineFunctions(self) -> None:
        """
        Propagate the failure of an asynchronous callable.

        Validates that the direct await path re-raises the original error.
        """
        with self.assertRaises(RuntimeError):
            await Loop.execute(coroutine_raising, RuntimeError, "boom")

class TestEventLoopContextManager(TestCase):

    def testProvidesAnOpenLoopAndLeavesItUsable(self) -> None:
        """
        Hand out a usable loop and keep it open after the block.

        Validates that a context without pending work performs no cleanup
        and never closes the loop it borrowed.
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
        """
        task = call_off_loop(context_cancelling_pending_task)
        self.assertTrue(task.cancelled())

    def testToleratesALoopClosedInsideTheBlock(self) -> None:
        """
        Leave the context silently when the loop was closed inside it.

        Validates that the cleanup never lets a ``RuntimeError`` escape the
        ``finally`` block.
        """
        self.assertTrue(call_off_loop(context_with_a_closed_loop))

    def testSkipsTheCleanupWhileTheLoopIsRunning(self) -> None:
        """
        Skip the cleanup when the borrowed loop is still running.

        Validates that a context opened inside asynchronous code never
        cancels the tasks driving the caller.
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
        """
        task = await Loop.createTask(coroutine_returning(5))
        self.assertIsInstance(task, asyncio.Task)
        self.assertEqual(await task, 5)

    async def testAppliesTheRequestedTaskName(self) -> None:
        """
        Apply the descriptive name given to the task.

        Validates that the optional name reaches the underlying asyncio
        call so tasks stay identifiable while debugging.
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
        """
        result = call_off_loop(Loop.runSync, coroutine_returning("direct"))
        self.assertEqual(result, "direct")

    def testDispatchesToTheWorkerWhileALoopIsRunning(self) -> None:
        """
        Dispatch the coroutine to the shared worker inside a live loop.

        Validates that synchronous callers can reach asynchronous code
        without deadlocking the loop that invoked them.
        """
        self.assertTrue(Loop.isLoopRunning())
        self.assertEqual(Loop.runSync(coroutine_returning("bridged")), "bridged")

    def testPropagatesExceptionsRaisedByTheCoroutine(self) -> None:
        """
        Propagate coroutine failures through the synchronous bridge.

        Validates that the worker future re-raises the original error in
        the calling thread.
        """
        self.assertTrue(Loop.isLoopRunning())
        with self.assertRaises(RuntimeError):
            Loop.runSync(coroutine_raising(RuntimeError, "boom"))
