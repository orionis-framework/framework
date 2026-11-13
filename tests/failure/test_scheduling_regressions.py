# ruff: noqa: PT009, PT027, S603
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Execute only this fixed regression script with the current Python interpreter.
"""Protect coroutine ownership when an event-loop task factory rejects work."""

from __future__ import annotations

import asyncio
import gc
import inspect
import io
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from contextvars import copy_context
from functools import partial
from textwrap import dedent
from typing import TYPE_CHECKING
from weakref import ref

from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.runtime import capture_nowait, operation
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from concurrent.futures import Future
    from weakref import ReferenceType


class _RetainedError(Exception):
    """Allow weak-reference observation of the original report exception."""


class _NoPlanHandler:
    """Observe an incident without retaining it or returning deferred effects."""

    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> None:
        """Complete the application hook without retaining any arguments."""


async def _completed_worker_report() -> tuple[
    Future,
    dict[str, ReferenceType[object]],
]:
    """Return a terminal future after its worker and operation have released work."""
    app, runtime, _ = activate_runtime()
    runtime.handler = _NoPlanHandler()
    original = _RetainedError("completed worker report")
    references = {
        "app": ref(app),
        "runtime": ref(runtime),
        "exception": ref(original),
    }
    try:
        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            operation(app, flow="worker", isolated=True),
        ):
            future = await asyncio.get_running_loop().run_in_executor(
                executor,
                copy_context().run,
                partial(capture_nowait, original, app=app),
            )
            await asyncio.wrap_future(future)
            await runtime.drain()
    finally:
        await runtime.shutdown()
    return future, references


class _RejectingFactory:
    """Record the real rejected coroutines and always raise one controlled error."""

    __slots__ = ("error", "rejected")

    def __init__(self, error: Exception) -> None:
        """Retain the scheduling error and coroutine references for verification."""
        self.error = error
        self.rejected: list[Coroutine] = []

    def __call__(
        self,
        _loop: asyncio.AbstractEventLoop,
        coroutine: Coroutine,
        **_kwargs: object,
    ) -> asyncio.Task:
        """Reject admission without assuming ownership of the coroutine."""
        self.rejected.append(coroutine)
        raise self.error

    def close(self) -> None:
        """Close any leaked coroutine after assertions, including a failed test."""
        for coroutine in self.rejected:
            coroutine.close()


class TestFailureSchedulingRegressions(IsolatedFailureTestCase):
    """Use real runtime scheduling with controlled failures at task admission."""

    async def testLoopSchedulingFailureReleasesTheClaimAndCoroutine(self) -> None:
        """Release a rejected report so its incident can be retried."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        loop = asyncio.get_running_loop()
        previous = loop.get_task_factory()
        factory = _RejectingFactory(RuntimeError("task admission rejected"))
        self.addCleanup(factory.close)
        original = ValueError("primary failure")
        with operation(app, flow="http"), redirect_stderr(io.StringIO()):
            loop.set_task_factory(factory)
            try:
                self.assertIsNone(capture_nowait(original, app=app))
            finally:
                loop.set_task_factory(previous)
            self.assertEqual(len(factory.rejected), 1)
            self.assertEqual(
                inspect.getcoroutinestate(factory.rejected[0]),
                inspect.CORO_CLOSED,
            )
            plan = await asyncio.wait_for(
                runtime.handlingFor(original, context=FailureContext(flow="http")),
                timeout=1,
            )
        self.assertIsInstance(plan, FailureHandling)
        self.assertEqual(handler.reports, [original])

    async def testThreadSchedulingFailureClosesWorkAndReportsOnce(self) -> None:
        """Complete the worker's future without leaking rejected work."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        loop = asyncio.get_running_loop()
        previous_factory = loop.get_task_factory()
        previous_handler = loop.get_exception_handler()
        rejected = TypeError("task factory rejected its call signature")
        factory = _RejectingFactory(rejected)
        self.addCleanup(factory.close)
        loop_errors = []
        original = ValueError("primary worker failure")
        with operation(app, flow="http"), redirect_stderr(io.StringIO()):
            loop.set_exception_handler(
                lambda _loop, context: loop_errors.append(context),
            )
            loop.set_task_factory(factory)
            try:
                pending = await asyncio.to_thread(capture_nowait, original, app=app)
                with self.assertRaises(TypeError) as raised:
                    await asyncio.wrap_future(pending)
                self.assertIs(raised.exception, rejected)
            finally:
                loop.set_task_factory(previous_factory)
                loop.set_exception_handler(previous_handler)
            self.assertEqual(len(factory.rejected), 1)
            self.assertEqual(
                inspect.getcoroutinestate(factory.rejected[0]),
                inspect.CORO_CLOSED,
            )
            self.assertEqual(loop_errors, [])
            plan = await asyncio.wait_for(
                runtime.handlingFor(original, context=FailureContext(flow="http")),
                timeout=1,
            )
        self.assertIsInstance(plan, FailureHandling)
        self.assertEqual(handler.reports, [original])

    async def testRejectedTaskPreservesCallerOwnershipOfTheOriginal(self) -> None:
        """Close the runtime wrapper while preserving work not admitted by the loop."""
        _, runtime, _ = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        loop = asyncio.get_running_loop()
        previous = loop.get_task_factory()
        rejected = RuntimeError("application task admission rejected")
        factory = _RejectingFactory(rejected)
        self.addCleanup(factory.close)
        result = object()

        async def work() -> object:
            """Return a caller-owned result when the original coroutine is awaited."""
            return result

        original = work()
        self.addCleanup(original.close)
        loop.set_task_factory(factory)
        try:
            with self.assertRaises(RuntimeError) as raised:
                runtime.createTask(original)
        finally:
            loop.set_task_factory(previous)
        self.assertIs(raised.exception, rejected)
        self.assertEqual(len(factory.rejected), 1)
        self.assertIsNot(factory.rejected[0], original)
        self.assertEqual(
            inspect.getcoroutinestate(factory.rejected[0]),
            inspect.CORO_CLOSED,
        )
        self.assertEqual(inspect.getcoroutinestate(original), inspect.CORO_CREATED)
        self.assertIs(await original, result)

    async def testCancelledThreadReportRemainsOwnedUntilItsCleanupCompletes(
        self,
    ) -> None:
        """Keep loop-side cleanup owned after the worker future cancels."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        entered = asyncio.Event()
        cleanup_started = asyncio.Event()
        release_cleanup = asyncio.Event()
        report_tasks = []

        async def log(_exception: BaseException) -> None:
            """Hold cancellation cleanup until the test releases its event."""
            report_tasks.append(asyncio.current_task())
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleanup_started.set()
                await release_cleanup.wait()

        handler.log = log
        draining = None
        try:
            with operation(app, flow="http"):
                pending = await asyncio.to_thread(
                    capture_nowait,
                    ValueError("cancelled worker report"),
                    app=app,
                )
                await asyncio.wait_for(entered.wait(), timeout=1)
                self.assertTrue(pending.cancel())
                await asyncio.wait_for(cleanup_started.wait(), timeout=1)
                draining = asyncio.create_task(runtime.drain())
                checkpoint = asyncio.Event()
                asyncio.get_running_loop().call_soon(checkpoint.set)
                await checkpoint.wait()
                self.assertFalse(draining.done())
                release_cleanup.set()
                await asyncio.wait_for(draining, timeout=1)
                self.assertTrue(pending.cancelled())
        finally:
            release_cleanup.set()
            for task in report_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*report_tasks, return_exceptions=True)
            if draining is not None:
                await asyncio.wait_for(draining, timeout=1)

    async def testCompletedWorkerFutureReleasesItsApplicationAndOriginal(self) -> None:
        """Release the retired delivery owner while retaining its receipt future."""
        future, references = await _completed_worker_report()
        await asyncio.sleep(0)
        gc.collect()
        for name, reference in references.items():
            with self.subTest(reference=name):
                self.assertIsNone(reference())
        self.assertTrue(future.done())
        self.assertTrue(future.result().delivered)
        self.assertFalse(future.result().reported)

    async def testUnstartedWrapperRetainsItsAlreadyRunningTaskUntilCleanup(
        self,
    ) -> None:
        """Join admitted task cleanup and observe its original failure once."""
        for supervised, cleanup_error in (
            (False, None),
            (False, ValueError("adopted task cleanup")),
            (True, None),
            (True, ValueError("supervised task cleanup")),
        ):
            with self.subTest(supervised=supervised, cleanup_error=cleanup_error):
                _, runtime, handler = activate_runtime()
                entered = asyncio.Event()
                cleanup_started = asyncio.Event()
                release_cleanup = asyncio.Event()

                async def work(
                    *,
                    error: Exception | None = cleanup_error,
                    ready: asyncio.Event = entered,
                    cleanup_ready: asyncio.Event = cleanup_started,
                    release: asyncio.Event = release_cleanup,
                ) -> None:
                    """Wait for cancellation and complete cleanup only on release."""
                    ready.set()
                    try:
                        await asyncio.Event().wait()
                    finally:
                        cleanup_ready.set()
                        await release.wait()
                        if error is not None:
                            raise error

                original = (
                    runtime.createTask(work())
                    if supervised
                    else asyncio.create_task(work())
                )
                wrappers = []
                closing = None
                try:
                    await asyncio.wait_for(entered.wait(), timeout=1)
                    if supervised and cleanup_error is not None:
                        original.cancel()
                    count = 2 if not supervised and cleanup_error is not None else 1
                    wrappers = [runtime.createTask(original) for _ in range(count)]
                    for wrapper in wrappers:
                        wrapper.cancel()
                    await asyncio.gather(*wrappers, return_exceptions=True)
                    await asyncio.wait_for(cleanup_started.wait(), timeout=1)
                    closing = asyncio.create_task(runtime.shutdown())
                    with self.assertRaises(TimeoutError):
                        await asyncio.wait_for(asyncio.shield(closing), timeout=0.05)
                    self.assertFalse(original.done())
                    release_cleanup.set()
                    await asyncio.wait_for(closing, timeout=1)
                    self.assertTrue(original.done())
                    expected = [] if cleanup_error is None else [cleanup_error]
                    self.assertEqual(handler.reports, expected)
                finally:
                    release_cleanup.set()
                    pending = [
                        task
                        for task in (original, *wrappers, closing)
                        if task is not None
                    ]
                    await asyncio.gather(*pending, return_exceptions=True)
                    await runtime.shutdown()

    def testAdoptedCleanupPreservesLifecycleReentryGuards(self) -> None:
        """Reject recursive startup and return from recursive shutdown and drain."""
        script = dedent('''
            import asyncio
            from tests.support.failure_runtime import activate_runtime

            async def main() -> None:
                """Exercise real reentry in an isolated process with bounded exit."""
                _, runtime, _ = activate_runtime()
                entered = asyncio.Event()
                cleanup_started = asyncio.Event()
                release = asyncio.Event()
                results = []

                async def work() -> None:
                    """Attempt lifecycle reentry while adopted cleanup is owned."""
                    entered.set()
                    try:
                        await asyncio.Event().wait()
                    finally:
                        cleanup_started.set()
                        await release.wait()
                        try:
                            await runtime.start(object())
                        except RuntimeError:
                            results.append("start rejected")
                        await runtime.shutdown()
                        results.append("shutdown returned")
                        await runtime.drain()
                        results.append("drain returned")

                original = runtime.createTask(work())
                wrapper = None
                closing = None
                try:
                    await entered.wait()
                    wrapper = runtime.createTask(original)
                    wrapper.cancel()
                    await asyncio.gather(wrapper, return_exceptions=True)
                    await cleanup_started.wait()
                    closing = asyncio.create_task(runtime.shutdown())
                    await asyncio.sleep(0)
                    release.set()
                    await asyncio.wait_for(asyncio.shield(closing), timeout=1)
                finally:
                    release.set()
                    if not original.done():
                        original.cancel()
                    pending = [task for task in (original, wrapper, closing)
                               if task is not None]
                    await asyncio.gather(*pending, return_exceptions=True)
                    await runtime.shutdown()
                assert results == [
                    "start rejected", "shutdown returned", "drain returned",
                ]

            asyncio.run(main())
        ''')
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
