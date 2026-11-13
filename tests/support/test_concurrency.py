# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import asyncio
import contextvars
import inspect
import threading
from typing import Self
from orionis.container.container import Container
from orionis.container.context.scope import reset_scope, set_current_scope
from orionis.support.concurrency import BoundedExecutor, WorkQueueFullError, threaded
from orionis.test import TestCase


class TestBoundedExecution(TestCase):
    """Exercise actual worker admission, context, injection and cancellation."""

    async def testThreadedCallbackPreservesInjectionAndContext(self: Self) -> None:
        """
        Resolve dependencies before crossing threads and preserve request context.

        Returns
        -------
        None
            No return value.
        """
        context = contextvars.ContextVar("test-request", default="absent")
        self.addCleanup(context.reset, context.set("request-one"))
        self.addCleanup(
            reset_scope,
            set_current_scope(None),
        )
        container = object.__new__(Container)
        Container.__init__(container)
        caller = threading.get_ident()

        @threaded
        def callback(value: str = "default") -> tuple:
            """
            Return the argument, request context and executing thread identifier.

            Parameters
            ----------
            value : str
                Value supplied for ``value``.

            Returns
            -------
            tuple
                Argument value, request context and worker thread identifier.
            """
            return value, context.get(), threading.get_ident()

        self.assertEqual(
            str(inspect.signature(callback)),
            "(value: str = 'default') -> tuple",
        )
        value, request, worker = await container.invoke(callback, value="provided")
        self.assertEqual((value, request), ("provided", "request-one"))
        self.assertNotEqual(caller, worker)

        class Dependency:
            pass

        container.singleton(Dependency, Dependency)

        @threaded
        def injected(dependency: Dependency) -> tuple[Dependency, str]:
            """
            Return the injected dependency and current request context.

            Parameters
            ----------
            dependency : Dependency
                Dependency resolved by the container before dispatch.

            Returns
            -------
            tuple[Dependency, str]
                Resolved dependency and current request context.
            """
            return dependency, context.get()

        dependency, request = await container.invoke(injected)
        self.assertIs(dependency, await container.make(Dependency))
        self.assertEqual(request, "request-one")

    async def testCancellationKeepsAdmissionUntilNativeCompletion(self: Self) -> None:
        """
        Retain a cancelled native call permit until the work finishes.

        Returns
        -------
        None
            No return value.
        """
        pool = BoundedExecutor(1, max_pending=0)
        entered, released = threading.Event(), threading.Event()

        def work() -> None:
            """
            Signal worker entry and wait for the test to release it.

            Returns
            -------
            None
                Complete the operation without returning a value.
            """
            entered.set()
            released.wait(5)

        task = asyncio.create_task(pool.run(work))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 5))
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            with self.assertRaises(WorkQueueFullError):
                await pool.run(lambda: None)
        finally:
            released.set()
            try:
                with self.assertRaises(asyncio.CancelledError):
                    await task
            finally:
                await pool.aclose()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            await pool.run(lambda: None)

    async def testQueuedCancellationReleasesCapacityWithoutExecuting(
        self: Self,
    ) -> None:
        """
        Cancel a pending call without running its side effects.

        Returns
        -------
        None
            No return value.
        """
        pool = BoundedExecutor(1, max_pending=1)
        entered, released = threading.Event(), threading.Event()
        calls = []

        def work() -> None:
            """
            Signal worker entry and wait for the test to release it.

            Returns
            -------
            None
                Complete the operation without returning a value.
            """
            entered.set()
            released.wait(5)

        running = asyncio.create_task(pool.run(work))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 5))
            queued = asyncio.create_task(pool.run(calls.append, "unexpected"))
            await asyncio.sleep(0)
            queued.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await queued
            self.assertEqual(calls, [])
        finally:
            released.set()
            try:
                await running
            finally:
                await pool.aclose()
