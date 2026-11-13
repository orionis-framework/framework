# ruff: noqa: FBT003, PLC0415, PT009, PT027, S603, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep runtime reflection annotations and intentionally deferred imports.
# Keep established public and external protocol names and signatures.
# Run a fixed probe in the active interpreter to bound the deadlock regression.
import asyncio
import concurrent.futures
import contextvars
import subprocess
import sys
import threading
import types
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import skipIf
from unittest.mock import patch
from orionis.aio.loop import Loop
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Generator

_NESTED_SYNC_PROBE = '''\
from orionis.aio import Loop

async def leaf() -> str:
    """Return the nested probe's sentinel value."""
    return "leaf"

async def middle() -> str:
    """Attempt a forbidden nested entry and close its rejected coroutine."""
    coro = leaf()
    try:
        return Loop.runSync(coro)
    finally:
        coro.close()

async def outer() -> str:
    """Attempt the outer nested entry without leaving an unawaited coroutine."""
    coro = middle()
    try:
        return Loop.runSync(coro)
    finally:
        coro.close()

try:
    Loop.runSync(outer())
except RuntimeError as error:
    print(error)
else:
    raise AssertionError("Nested runSync calls were not rejected")
'''


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


async def coroutine_raising(exception: type[BaseException], message: str) -> None:
    """Raise an exception from an asynchronous context.

    Parameters
    ----------
    exception : type[BaseException]
        Exception class to raise.
    message : str
        Message supplied to the exception.

    Raises
    ------
    BaseException
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


async def coroutine_pending() -> None:
    """Remain pending until the caller cancels the resulting task."""
    await asyncio.Event().wait()


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
    """Acquire a probe loop and report whether it was registered.

    Parameters
    ----------
    probe : type[Loop]
        Isolated loop manager to query.

    Returns
    -------
    tuple[asyncio.AbstractEventLoop, bool]
        The acquired loop and whether asyncio registers it as current.
    """
    loop = probe.getEventLoop()
    return loop, asyncio.get_event_loop() is loop


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
        return loop.create_task(coroutine_pending())


def context_with_a_closed_loop() -> None:
    """Close an owned loop before its context can clean up.

    Raises
    ------
    RuntimeError
        The owned loop was closed before managed cleanup.
    """
    with Loop.eventLoopContext() as loop:
        loop.close()


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
        """Publish the value as if a competing thread had produced it."""
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
        """Publish a stand-in module in the import cache."""
        self.module = new_fake_uvloop_module()
        module_patch = patch.dict(sys.modules, {"uvloop": self.module})
        module_patch.start()
        self.addCleanup(module_patch.stop)

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
        """Block the ``uvloop`` import for the test."""
        module_patch = patch.dict(sys.modules, {"uvloop": None})
        module_patch.start()
        self.addCleanup(module_patch.stop)

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


@skipIf(sys.platform == "win32", "uvloop is not supported on Windows")
class TestRealUvloopIntegration(TestCase):
    """Exercise the installed uvloop without substituting its factory."""

    def testRunsOnUvloopAndRestoresThePreviousLoop(self) -> None:
        """Execute work on uvloop and preserve the caller's registered loop."""
        import uvloop  # pyright: ignore[reportMissingImports]

        probe = new_loop_probe()

        async def run_work() -> asyncio.AbstractEventLoop:
            """
            Exercise loop lookup, task creation, and executor work.

            Returns
            -------
            asyncio.AbstractEventLoop
                Running loop used for lookup, task creation, and executor checks.
            """
            running = asyncio.get_running_loop()
            self.assertIs(probe.getEventLoop(), running)
            self.assertEqual(await probe.execute(sync_returning, "worker"), "worker")
            task = probe.createTask(coroutine_returning("task"))
            self.assertEqual(await task, "task")
            return running

        def check_runner() -> None:
            """Restore an idle external loop after closing the owned uvloop."""
            previous = asyncio.new_event_loop()
            asyncio.set_event_loop(previous)
            try:
                owned = probe.run(run_work())
                self.assertIsInstance(owned, uvloop.Loop)
                self.assertTrue(owned.is_closed())
                self.assertIs(asyncio.get_event_loop(), previous)
                self.assertFalse(previous.is_closed())
            finally:
                previous.close()
                asyncio.set_event_loop(None)

        call_off_loop(check_runner)

    def testOwnsUvloopAndCancelsPendingTasksOnContextExit(self) -> None:
        """Close a real uvloop and drain its pending tasks through Runner."""
        import uvloop  # pyright: ignore[reportMissingImports]

        probe = new_loop_probe()

        def check_context() -> None:
            """Verify registration, task cancellation, and loop cleanup."""
            with probe.eventLoopContext() as loop:
                self.assertIsInstance(loop, uvloop.Loop)
                self.assertIs(asyncio.get_event_loop(), loop)
                task = loop.create_task(coroutine_pending())
                loop.run_until_complete(asyncio.sleep(0))
            self.assertTrue(task.cancelled())
            self.assertTrue(loop.is_closed())
            with self.assertRaises(RuntimeError):
                asyncio.get_event_loop()

        call_off_loop(check_context)


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
        """Hide the Proactor loop exported by asyncio."""
        self.proactor = vars(asyncio).pop("ProactorEventLoop", None)

    def tearDown(self) -> None:
        """Restore the Proactor loop exported by asyncio."""
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


class TestEventLoopRetrieval(TestCase):
    def testReturnsTheLoopAlreadyRunningInTheThread(self) -> None:
        """
        Return the running loop without creating another one.

        Validates the fast path that prevents a second loop from being
        created inside asynchronous code.

        """
        self.assertIs(Loop.getEventLoop(), asyncio.get_running_loop())

    def testReusesTheRegisteredLoopInTheThread(self) -> None:
        """
        Reuse the very same loop for every call made by one thread.

        Validates that asyncio's registration avoids rebuilding a loop that
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

    def testReplacesTheRegisteredLoopOnceItIsClosed(self) -> None:
        """
        Replace the registered loop when it has already been closed.

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
        loop, registered = call_off_loop(acquire_probe_loop, probe)
        try:
            self.assertIsInstance(loop, asyncio.AbstractEventLoop)
            self.assertTrue(registered)
        finally:
            loop.close()

    def testFollowsAnExternallyReplacedRegistration(self) -> None:
        """Use the replacement registered through asyncio.set_event_loop."""

        def check_registration() -> None:
            """Replace an open loop in the same thread."""
            first = Loop.getEventLoop()
            replacement = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(replacement)
                self.assertIs(Loop.getEventLoop(), replacement)
                self.assertIs(asyncio.get_event_loop(), replacement)
                self.assertFalse(first.is_closed())
            finally:
                first.close()
                replacement.close()
                asyncio.set_event_loop(None)

        call_off_loop(check_registration)

    def testDoesNotReuseAnUnregisteredLoop(self) -> None:
        """Create a fresh loop after the caller clears the registration."""

        def check_registration() -> None:
            """Clear the registry without closing its previous loop."""
            first = Loop.getEventLoop()
            asyncio.set_event_loop(None)
            replacement = Loop.getEventLoop()
            try:
                self.assertIsNot(first, replacement)
                self.assertIs(asyncio.get_event_loop(), replacement)
                self.assertFalse(first.is_closed())
            finally:
                first.close()
                replacement.close()
                asyncio.set_event_loop(None)

        call_off_loop(check_registration)


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

    def testPropagatesKeyboardInterrupt(self) -> None:
        """
        Propagate interruption without substituting a return value.

        Validates that the entry point preserves the coroutine's result type
        and lets the application choose its interruption policy.

        """
        with self.assertRaises(KeyboardInterrupt):
            call_off_loop(Loop.run, coroutine_interrupted())

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

        Validates the documented failure mode, including that no runner is
        opened and the coroutine stays the caller's to close.

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

    def testRegistersFactoryLoopsBeforeExecutionAndClearsThemAfterward(self) -> None:
        """Register both optimal and fallback loops before Runner.run starts."""

        def check_registration() -> None:
            """Observe the current loop before entering asynchronous code."""
            run = asyncio.Runner.run
            created = []

            def run_registered(
                runner: asyncio.Runner,
                coro: Awaitable[object],
            ) -> object:
                """
                Check the loop registry before running the coroutine.

                Parameters
                ----------
                runner : asyncio.Runner
                    Runner whose loop must already be registered.
                coro : Awaitable[object]
                    Awaitable delegated to the original runner method.

                Returns
                -------
                object
                    Result produced by the delegated awaitable.
                """
                loop = runner.get_loop()
                created.append(loop)
                self.assertIs(asyncio.get_event_loop(), loop)
                return run(runner, coro)

            for factory in (None, asyncio.new_event_loop):
                probe = new_loop_probe(
                    _loop_factory_resolved=True,
                    _loop_factory_cached=factory,
                )
                with patch.object(asyncio.Runner, "run", run_registered):
                    self.assertEqual(probe.run(coroutine_returning(42)), 42)
                self.assertTrue(created[-1].is_closed())
                with self.assertRaises(RuntimeError):
                    asyncio.get_event_loop()

        call_off_loop(check_registration)

    def testRestoresThePreviousLoopAfterResultsAndExceptions(self) -> None:
        """Restore a borrowed registration on success, failure and interruption."""

        def check_restoration() -> None:
            """Keep the outer owner's loop usable across nested entry points."""
            with asyncio.Runner() as owner:
                previous = owner.get_loop()
                for factory in (None, asyncio.new_event_loop):
                    probe = new_loop_probe(
                        _loop_factory_resolved=True,
                        _loop_factory_cached=factory,
                    )
                    self.assertEqual(probe.run(coroutine_returning(42)), 42)
                    self.assertIs(asyncio.get_event_loop(), previous)
                    for exception in (
                        ValueError,
                        KeyboardInterrupt,
                        asyncio.CancelledError,
                    ):
                        with self.assertRaises(exception):
                            probe.run(coroutine_raising(exception, "interrupted"))
                        self.assertIs(asyncio.get_event_loop(), previous)
                        self.assertFalse(previous.is_closed())

        call_off_loop(check_restoration)

    def testDoesNotRestoreAPreviousLoopClosedDuringExecution(self) -> None:
        """Clear the registry if the previous loop has been closed."""

        def check_restoration() -> None:
            """Close the previous idle loop while the owned loop runs."""
            previous = asyncio.new_event_loop()
            asyncio.set_event_loop(previous)
            try:

                async def close_previous() -> None:
                    """Close the previous registration from a separate loop."""
                    previous.close()

                Loop.run(close_previous())
                with self.assertRaises(RuntimeError):
                    asyncio.get_event_loop()
            finally:
                previous.close()
                asyncio.set_event_loop(None)

        call_off_loop(check_restoration)


class TestExecuteBridge(TestCase):
    async def testOffloadsSynchronousCallablesToTheExecutor(self) -> None:
        """
        Run a blocking callable outside the loop thread.

        Validate that the synchronous callable runs on a worker thread.

        """
        worker_thread = await Loop.execute(threading.get_ident)
        self.assertNotEqual(worker_thread, threading.get_ident())

    async def testAwaitsCoroutineFunctionsDirectly(self) -> None:
        """
        Await a coroutine function without using the executor.

        Validate that the coroutine body runs on the invoking loop.

        """

        async def running_loop() -> asyncio.AbstractEventLoop:
            """Return the loop used to execute this coroutine.

            Returns
            -------
            asyncio.AbstractEventLoop
                Loop running the coroutine body.
            """
            return asyncio.get_running_loop()

        self.assertIs(await Loop.execute(running_loop), asyncio.get_running_loop())

    async def testForwardsKeywordArgumentsToSynchronousCallables(self) -> None:
        """
        Forward keyword arguments to the blocking callable.

        Validates that to_thread forwards keywords without changing the
        calling convention.

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

    async def testAwaitsGeneratorBasedCoroutines(self) -> None:
        """Resolve generator-based coroutines on the calling event loop."""
        running = asyncio.get_running_loop()

        @types.coroutine
        def generator_coroutine() -> Generator[None, None, str]:
            """
            Suspend once before returning from the caller's loop.

            Returns
            -------
            str
                Sentinel result delivered when the coroutine completes.

            Yields
            ------
            None
                Suspend once on the caller's event loop.
            """
            yield
            self.assertIs(asyncio.get_running_loop(), running)
            return "generator-result"

        self.assertEqual(
            await Loop.execute(generator_coroutine),
            "generator-result",
        )

    async def testPropagatesGeneratorBasedCoroutineFailures(self) -> None:
        """Propagate errors raised after a generator-based coroutine suspends."""

        @types.coroutine
        def failing_coroutine() -> Generator[None]:
            """
            Suspend once before raising the original application error.

            Yields
            ------
            None
                Suspend once before simulating an application failure.

            Raises
            ------
            ValueError
                Always raised after the initial suspension.
            """
            yield
            error_msg = "generator failure"
            raise ValueError(error_msg)

        with self.assertRaisesRegex(ValueError, "generator failure"):
            await Loop.execute(failing_coroutine)

    async def testReturnsOrdinaryGeneratorsWithoutAwaitingThem(self) -> None:
        """Preserve generators that do not implement the awaitable protocol."""

        def values() -> Generator[str]:
            """
            Yield an ordinary synchronous value.

            Yields
            ------
            str
                Sentinel value from an ordinary synchronous generator.
            """
            yield "ordinary-generator"

        generator = values()
        try:
            result = await Loop.execute(sync_returning, generator)
            self.assertIs(result, generator)
            self.assertEqual(list(result), ["ordinary-generator"])
        finally:
            generator.close()

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

    async def testCopiesContextIntoTheWorkerWithoutLeakingChanges(self) -> None:
        """Preserve request context while isolating worker-side modifications."""
        marker = contextvars.ContextVar("execute-request", default="missing")
        caller_thread = threading.get_ident()
        token = marker.set("request-id")

        def read_and_modify_context() -> tuple[str, int]:
            """
            Read the inherited context and modify only the worker copy.

            Returns
            -------
            tuple[str, int]
                Inherited context value and identifier of the worker thread.
            """
            value = marker.get()
            marker.set("worker")
            return value, threading.get_ident()

        try:
            value, worker_thread = await Loop.execute(read_and_modify_context)
            self.assertEqual(value, "request-id")
            self.assertNotEqual(worker_thread, caller_thread)
            self.assertEqual(marker.get(), "request-id")
        finally:
            marker.reset(token)


class TestEventLoopContextManager(TestCase):
    def testClosesTheLoopItCreates(self) -> None:
        """
        Hand out a usable loop and close it after the block.

        Validates that a context without a registered loop owns and closes
        the loop it creates, even without pending tasks.

        """
        loop, open_inside = call_off_loop(context_without_pending_tasks)
        self.assertTrue(open_inside)
        self.assertTrue(loop.is_closed())

    def testCancelsThePendingTasksOnExit(self) -> None:
        """
        Cancel and drain the tasks still pending when the block ends.

        Validates the cooperative cleanup that prevents orphan tasks from
        outliving the context.

        """
        task = call_off_loop(context_cancelling_pending_task)
        self.assertTrue(task.cancelled())

    def testReportsALoopClosedBeforeCleanup(self) -> None:
        """
        Report an owned loop closed before its cleanup can finish.

        Validates that lifecycle violations are not silently swallowed and
        cleanup does not create unawaited shutdown coroutines.

        """
        with self.assertRaisesRegex(RuntimeError, "closed before cleanup"):
            call_off_loop(context_with_a_closed_loop)

    async def testBorrowsARunningLoopWithoutCancellingItsTasks(self) -> None:
        """
        Skip the cleanup when the borrowed loop is still running.

        Validates that a context opened inside asynchronous code never
        cancels the tasks driving the caller.

        """
        running = asyncio.get_running_loop()
        task = asyncio.create_task(coroutine_pending())
        try:
            with Loop.eventLoopContext() as loop:
                self.assertIs(loop, running)
            await asyncio.sleep(0)
            self.assertFalse(running.is_closed())
            self.assertFalse(task.done())
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def testNestedContextsLeaveOuterTasksUntouched(self) -> None:
        """Let only the owning outer context cancel its pending tasks."""

        def check_nested_contexts() -> None:
            """Borrow the registered loop from a nested idle context."""
            with Loop.eventLoopContext() as loop:
                task = loop.create_task(coroutine_pending())
                loop.run_until_complete(asyncio.sleep(0))
                with Loop.eventLoopContext() as inner:
                    self.assertIs(inner, loop)
                self.assertFalse(task.done())
                self.assertFalse(loop.is_closed())
            self.assertTrue(task.cancelled())
            self.assertTrue(loop.is_closed())

        call_off_loop(check_nested_contexts)

    def testBorrowsAnIdleLoopWithoutCancellingItsTasks(self) -> None:
        """Leave a loop owned by an external Runner open and untouched."""

        def check_borrowed_context() -> None:
            """Keep the external owner's tasks alive after context exit."""
            with asyncio.Runner() as owner:
                external = owner.get_loop()
                task = external.create_task(coroutine_pending())
                external.run_until_complete(asyncio.sleep(0))
                with Loop.eventLoopContext() as loop:
                    self.assertIs(loop, external)
                self.assertFalse(task.done())
                self.assertFalse(external.is_closed())
                self.assertIs(asyncio.get_event_loop(), external)
            self.assertTrue(task.cancelled())
            self.assertTrue(external.is_closed())

        call_off_loop(check_borrowed_context)

    def testBorrowsAPreviouslyRetrievedLoopWithoutTakingOwnership(self) -> None:
        """Leave a loop acquired through getEventLoop owned by its caller."""

        def check_borrowed_context() -> None:
            """Close the retrieved loop explicitly after the borrowing context."""
            retrieved = Loop.getEventLoop()
            try:
                with Loop.eventLoopContext() as current:
                    self.assertIs(current, retrieved)
                self.assertFalse(retrieved.is_closed())
                self.assertIs(asyncio.get_event_loop(), retrieved)
            finally:
                retrieved.close()
                asyncio.set_event_loop(None)

        call_off_loop(check_borrowed_context)

    def testFinalizesAsyncGeneratorsAndShutsDownTheDefaultExecutor(self) -> None:
        """Drain async generators and executor work before closing an owned loop."""

        def check_cleanup() -> None:
            """Release executor work from an async generator's finalizer."""
            released = threading.Event()
            completed = threading.Event()

            async def values() -> AsyncIterator[str]:
                """
                Yield once and release the worker when finalized.

                Yields
                ------
                str
                    Sentinel value whose generator finalization releases the worker.
                """
                try:
                    yield "value"
                finally:
                    released.set()

            def worker() -> bool:
                """
                Wait for generator finalization before completing.

                Returns
                -------
                bool
                    Whether generator finalization released the worker before timeout.
                """
                was_released = released.wait(timeout=2)
                completed.set()
                return was_released

            generator = values()

            async def first_value() -> str:
                """
                Start iteration with the running loop's async-generator hooks.

                Returns
                -------
                str
                    First value yielded by the asynchronous generator.
                """
                return await anext(generator)

            with Loop.eventLoopContext() as loop:
                self.assertEqual(loop.run_until_complete(first_value()), "value")
                future = loop.run_in_executor(None, worker)
                self.assertFalse(released.is_set())
            self.assertTrue(released.is_set())
            self.assertTrue(completed.is_set())
            self.assertTrue(future.result())
            self.assertTrue(loop.is_closed())
            with self.assertRaises(RuntimeError):
                asyncio.get_event_loop()

        call_off_loop(check_cleanup)

    def testCleansUpWhenTheContextBodyRaises(self) -> None:
        """Close the owned loop and clear its registry when the body fails."""

        def check_cleanup() -> None:
            """Raise an application error inside an owning context."""
            with (
                self.assertRaisesRegex(ValueError, "context failure"),
                Loop.eventLoopContext() as loop,
            ):
                task = loop.create_task(coroutine_pending())
                error_msg = "context failure"
                raise ValueError(error_msg)
            self.assertTrue(task.cancelled())
            self.assertTrue(loop.is_closed())
            with self.assertRaises(RuntimeError):
                asyncio.get_event_loop()

        call_off_loop(check_cleanup)


class TestTaskCreation(TestCase):
    async def testSchedulesTheCoroutineAsATask(self) -> None:
        """
        Schedule the coroutine on the running loop.

        Validates that the returned object is a task that resolves to the
        coroutine result.

        """
        task = Loop.createTask(coroutine_returning(5))
        self.assertIsInstance(task, asyncio.Task)
        self.assertEqual(await task, 5)

    async def testAppliesTheRequestedTaskName(self) -> None:
        """
        Apply the descriptive name given to the task.

        Validates that the optional name reaches the underlying asyncio
        call so tasks stay identifiable while debugging.

        """
        task = Loop.createTask(
            coroutine_returning(None),
            name="orionis-task",
        )
        self.assertEqual(task.get_name(), "orionis-task")
        await task

    async def testSchedulesImmediatelyAndCapturesTheCreationContext(self) -> None:
        """Start the task before it is awaited using its creation-time context."""
        marker = contextvars.ContextVar("task-context", default="missing")
        observed = []

        async def record() -> str:
            """
            Record the context inherited when the task was created.

            Returns
            -------
            str
                Completion sentinel after recording the task's inherited context.
            """
            observed.append(marker.get())
            return "done"

        token = marker.set("created")
        task = Loop.createTask(record())
        try:
            marker.set("later")
            await asyncio.sleep(0)
            self.assertEqual(observed, ["created"])
            self.assertTrue(task.done())
            self.assertEqual(await task, "done")
        finally:
            marker.reset(token)
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


class TestRunSyncBridge(TestCase):
    def testRunsTheCoroutineDirectlyWithoutARunningLoop(self) -> None:
        """
        Drive the coroutine in place when no loop is running.

        Validates that the synchronous bridge avoids the worker thread
        whenever the caller owns the thread.

        """
        result = call_off_loop(Loop.runSync, coroutine_returning("direct"))
        self.assertEqual(result, "direct")

    def testRejectsARunningLoopWithoutConsumingTheCoroutine(self) -> None:
        """
        Refuse to synchronously wait from a running loop's thread.

        Validates that the caller receives an actionable error before a
        Runner or worker starts, retaining ownership of the coroutine.

        """
        self.assertTrue(Loop.isLoopRunning())
        coro = coroutine_returning("not consumed")
        try:
            with patch.object(asyncio, "Runner") as runner:
                with self.assertRaisesRegex(RuntimeError, "await the coroutine"):
                    Loop.runSync(coro)
                runner.assert_not_called()
            self.assertIsNotNone(coro.cr_frame)
        finally:
            coro.close()

    def testPropagatesExceptionsRaisedByTheCoroutine(self) -> None:
        """
        Propagate coroutine failures through the synchronous bridge.

        Validates that the synchronous entry point re-raises the original
        error in the calling thread.

        """
        with self.assertRaisesRegex(RuntimeError, "boom"):
            call_off_loop(Loop.runSync, coroutine_raising(RuntimeError, "boom"))

    def testRejectsInvalidInputsBeforeCheckingForARunningLoop(self) -> None:
        """Preserve coroutine validation even when the calling loop is active."""
        with self.assertRaises(TypeError):
            Loop.runSync(42)  # type: ignore[arg-type]

    def testRejectsNestedCallsInsteadOfDeadlocking(self) -> None:
        """Bound the nested single-worker deadlock regression in a subprocess."""
        result = subprocess.run(
            [sys.executable, "-B", "-c", _NESTED_SYNC_PROBE],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("await the coroutine", result.stdout)
        self.assertNotIn("was never awaited", result.stderr)

    async def testPreservesContextWhenExplicitlyOffloaded(self) -> None:
        """Carry request context through execute into a worker's sync entry point."""
        marker = contextvars.ContextVar("sync-request", default="missing")
        caller_thread = threading.get_ident()

        async def read_context() -> tuple[str, int]:
            """
            Read context from the worker's owned loop.

            Returns
            -------
            tuple[str, int]
                Inherited context value and identifier of the worker thread.
            """
            return marker.get(), threading.get_ident()

        token = marker.set("request-id")
        try:
            value, worker_thread = await Loop.execute(Loop.runSync, read_context())
            self.assertEqual(value, "request-id")
            self.assertNotEqual(worker_thread, caller_thread)
            self.assertEqual(marker.get(), "request-id")
        finally:
            marker.reset(token)

    async def testSupportsConcurrentIndependentSynchronousCallers(self) -> None:
        """Run independent synchronous entry points without shared worker state."""
        results = await asyncio.gather(
            *(
                Loop.execute(Loop.runSync, coroutine_returning(value))
                for value in range(4)
            ),
        )
        self.assertEqual(results, list(range(4)))
