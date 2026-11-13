# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect cancellation and ownership at the synchronous callable bridge."""

import asyncio
import inspect
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING
from orionis.aio import Loop
from orionis.failure.runtime import operation
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator, Iterator


async def _result() -> None:
    """Provide a native coroutine whose lifecycle can be inspected.

    Returns
    -------
    None
        No return value.
    """


async def _cancel_running_call(callback: Callable[[], object]) -> None:
    """Cancel the bridge while its real worker waits to invoke a callback.

    Parameters
    ----------
    callback : Callable[[], object]
        Callable executed after cancellation has reached the bridge.

    Returns
    -------
    None
        No return value.
    """
    loop = asyncio.get_running_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
    started = asyncio.Event()
    release = threading.Event()

    def work() -> object:
        """Wait for cancellation before evaluating the callback.

        Returns
        -------
        object
            Callback result returned after the caller has cancelled.
        """
        loop.call_soon_threadsafe(started.set)
        release.wait()
        return callback()

    task = asyncio.create_task(Loop.execute(work))
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            message = "The callable bridge did not propagate cancellation."
            raise AssertionError(message)
    finally:
        release.set()
        # Finish worker callbacks as the owning loop would during shutdown.
        await loop.shutdown_default_executor()


class TestWorkerCancellation(IsolatedFailureTestCase):
    """Exercise real executor completion after the caller is cancelled."""

    async def testCancellationClosesALateCoroutineResult(self) -> None:
        """Close a worker's coroutine when cancellation prevents awaiting it.

        Returns
        -------
        None
            No return value.
        """
        returned: list[Coroutine] = []

        def work() -> Coroutine:
            """Return a coroutine after the caller releases the worker.

            Returns
            -------
            Coroutine
                Newly created coroutine whose owner has been cancelled.
            """
            coroutine = _result()
            returned.append(coroutine)
            return coroutine

        await _cancel_running_call(work)
        self.assertEqual(len(returned), 1)
        try:
            self.assertEqual(
                inspect.getcoroutinestate(returned[0]),
                inspect.CORO_CLOSED,
            )
        finally:
            returned[0].close()

    async def testCancellationCancelsALateFutureResult(self) -> None:
        """Cancel a future returned after its bridge caller was cancelled.

        Returns
        -------
        None
            No return value.
        """
        future = asyncio.get_running_loop().create_future()
        try:
            await _cancel_running_call(lambda: future)
            self.assertTrue(future.cancelled())
        finally:
            future.cancel()

    async def testCancellationClosesALateGeneratorCoroutine(self) -> None:
        """Close a generator-based coroutine abandoned by bridge cancellation.

        Returns
        -------
        None
            No return value.
        """

        @types.coroutine
        def legacy() -> Generator[None]:
            """Provide a legacy coroutine with an inspectable lifecycle.

            Yields
            ------
            None
                Cooperative coroutine checkpoint.
            """
            yield

        coroutine = legacy()
        try:
            await _cancel_running_call(lambda: coroutine)
            self.assertEqual(inspect.getgeneratorstate(coroutine), inspect.GEN_CLOSED)
        finally:
            coroutine.close()

    async def testLateWorkerFailureReachesTheLoopHandlerOnce(self) -> None:
        """Observe worker failures whose caller has already cancelled.

        Returns
        -------
        None
            No return value.
        """
        loop = asyncio.get_running_loop()
        original = loop.get_exception_handler()
        contexts = []
        error = ValueError("controlled worker failure")

        def handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
            """Record the loop's real exception notification.

            Parameters
            ----------
            _loop : asyncio.AbstractEventLoop
                Loop delivering the notification.
            context : dict
                Original exception and completed worker future.

            Returns
            -------
            None
                No return value.
            """
            contexts.append(context)

        def work() -> None:
            """Raise the controlled worker error after cancellation.

            Returns
            -------
            None
                No return value.

            Raises
            ------
            ValueError
                Always raise the controlled worker error.
            """
            raise error

        loop.set_exception_handler(handler)
        try:
            await _cancel_running_call(work)
        finally:
            loop.set_exception_handler(original)
        self.assertEqual(len(contexts), 1)
        self.assertIs(contexts[0]["exception"], error)

    async def testLateWorkerFailureUsesTheActiveCoordinator(self) -> None:
        """Route a late worker error through the active failure runtime once.

        Returns
        -------
        None
            No return value.
        """
        _, runtime, handler = activate_runtime()
        loop = asyncio.get_running_loop()
        original = loop.get_exception_handler()
        fallback = []
        error = ValueError("controlled active-runtime worker failure")

        def work() -> None:
            """Raise the worker failure retained by the coordinator.

            Returns
            -------
            None
                No return value.

            Raises
            ------
            ValueError
                Always raise the controlled failure.
            """
            raise error

        loop.set_exception_handler(lambda _loop, context: fallback.append(context))
        try:
            with operation(runtime=runtime):
                await _cancel_running_call(work)
                await runtime.drain()
            self.assertEqual(handler.reports, [error])
            self.assertEqual(fallback, [])
        finally:
            await runtime.shutdown()
            loop.set_exception_handler(original)

    async def testLateFutureIsCancelledOnItsOwnLoop(self) -> None:
        """Schedule late future cancellation on its owning event-loop thread.

        Returns
        -------
        None
            No return value.
        """
        caller = asyncio.get_running_loop()
        ready = asyncio.Event()
        finished = asyncio.Event()
        foreign = asyncio.new_event_loop()
        foreign.set_debug(True)
        future = foreign.create_future()

        def run_foreign_loop() -> None:
            """Own the foreign loop until its future's callback stops it.

            Returns
            -------
            None
                No return value.
            """
            asyncio.set_event_loop(foreign)
            future.add_done_callback(lambda _future: foreign.stop())
            foreign.call_soon(caller.call_soon_threadsafe, ready.set)
            try:
                foreign.run_forever()
            finally:
                foreign.close()
                caller.call_soon_threadsafe(finished.set)

        thread = threading.Thread(target=run_foreign_loop)
        thread.start()
        try:
            await asyncio.wait_for(ready.wait(), timeout=5)
            await _cancel_running_call(lambda: future)
            await asyncio.wait_for(finished.wait(), timeout=5)
            self.assertTrue(future.cancelled())
        finally:
            if not foreign.is_closed():
                foreign.call_soon_threadsafe(foreign.stop)
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())

    async def testAbandonedAwaitableCleanupUsesTheActiveCoordinator(self) -> None:
        """Preserve a failed awaitable close through the active failure runtime.

        Returns
        -------
        None
            No return value.
        """
        _, runtime, handler = activate_runtime()
        error = OSError("controlled abandoned awaitable cleanup")

        class FailingAwaitable:
            """Expose a close failure without performing asynchronous work."""

            __slots__ = ()

            def __await__(self) -> Iterator[object]:
                """Return an empty iterator for the awaitable protocol.

                Returns
                -------
                Iterator[object]
                    Empty await iterator.
                """
                return iter(())

            def close(self) -> None:
                """Raise the original cleanup error.

                Returns
                -------
                None
                    No return value.

                Raises
                ------
                OSError
                    Always raise the controlled cleanup error.
                """
                raise error

        try:
            with operation(runtime=runtime):
                await _cancel_running_call(FailingAwaitable)
                await runtime.drain()
            self.assertEqual(handler.reports, [error])
        finally:
            await runtime.shutdown()

    async def testCompletedAbandonedFutureReportsItsOriginalFailure(self) -> None:
        """Observe an abandoned future that failed before cancellation.

        Returns
        -------
        None
            No return value.
        """
        _, runtime, handler = activate_runtime()
        error = OSError("completed abandoned future failure")
        future = asyncio.get_running_loop().create_future()
        future.set_exception(error)
        try:
            with operation(runtime=runtime):
                await _cancel_running_call(lambda: future)
                await runtime.drain()
            self.assertEqual(handler.reports, [error])
        finally:
            future.exception()
            await runtime.shutdown()

    async def testForeignFutureFailureWinsTheCancellationRace(self) -> None:
        """Observe a foreign future that fails before queued cancellation runs.

        Returns
        -------
        None
            No return value.
        """
        _, runtime, handler = activate_runtime()
        caller = asyncio.get_running_loop()
        ready, finished = asyncio.Event(), asyncio.Event()
        release = threading.Event()
        foreign = asyncio.new_event_loop()
        foreign.set_debug(True)
        future = foreign.create_future()
        error = OSError("foreign future completed before queued cancellation")

        def block_foreign_loop() -> None:
            """Hold the owner until failure and cancellation are queued in order.

            Returns
            -------
            None
                No return value.
            """
            caller.call_soon_threadsafe(ready.set)
            release.wait()

        def run_foreign_loop() -> None:
            """Run the future owner until its completion callback stops it.

            Returns
            -------
            None
                No return value.
            """
            asyncio.set_event_loop(foreign)
            future.add_done_callback(lambda _future: foreign.stop())
            foreign.call_soon(block_foreign_loop)
            try:
                foreign.run_forever()
            finally:
                foreign.close()
                caller.call_soon_threadsafe(finished.set)

        def work() -> asyncio.Future:
            """Queue failure ahead of the cleanup callback and return its future.

            Returns
            -------
            asyncio.Future
                Foreign future whose failure will precede cancellation.
            """
            foreign.call_soon_threadsafe(future.set_exception, error)
            return future

        thread = threading.Thread(target=run_foreign_loop)
        thread.start()
        try:
            await asyncio.wait_for(ready.wait(), timeout=5)
            with operation(runtime=runtime):
                await _cancel_running_call(work)
                release.set()
                await asyncio.wait_for(finished.wait(), timeout=5)
                await runtime.drain()
            self.assertEqual(handler.reports, [error])
        finally:
            release.set()
            if not foreign.is_closed():
                foreign.call_soon_threadsafe(foreign.stop)
            thread.join(timeout=5)
            if future.done() and not future.cancelled():
                future.exception()
            await runtime.shutdown()
        self.assertFalse(thread.is_alive())

    async def testCancellationPreventsQueuedCallableExecution(self) -> None:
        """Leave a queued callable unexecuted after its caller cancels.

        Returns
        -------
        None
            No return value.
        """
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        started = asyncio.Event()
        submitted = asyncio.Event()
        release = threading.Event()
        executed = threading.Event()

        def occupy_worker() -> None:
            """Keep the sole worker busy until the bridge is cancelled.

            Returns
            -------
            None
                No return value.
            """
            loop.call_soon_threadsafe(started.set)
            release.wait()

        blocker = asyncio.create_task(asyncio.to_thread(occupy_worker))
        try:
            await asyncio.wait_for(started.wait(), timeout=5)
            task = asyncio.create_task(Loop.execute(executed.set))
            loop.call_soon(submitted.set)
            await submitted.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            release.set()
            await blocker
            await loop.shutdown_default_executor()
        self.assertFalse(executed.is_set())
