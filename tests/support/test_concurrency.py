import asyncio
import contextvars
import inspect
import threading
from typing import Self
from orionis.container.container import Container
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
            Complete the assertions without returning a value.
        """
        context = contextvars.ContextVar("test-request", default="absent")
        context.set("request-one")
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
        value, request, worker = await Container().invoke(callback, value="provided")
        self.assertEqual((value, request), ("provided", "request-one"))
        self.assertNotEqual(caller, worker)

        class Dependency:
            pass

        container = Container()
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
            Complete the assertions without returning a value.
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
            await asyncio.to_thread(entered.wait, 5)
            task.cancel()
            await asyncio.sleep(0.01)
            self.assertFalse(task.done())
            with self.assertRaises(WorkQueueFullError):
                await pool.run(lambda: None)
        finally:
            released.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
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
            Complete the assertions without returning a value.
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
            await asyncio.to_thread(entered.wait, 5)
            queued = asyncio.create_task(pool.run(calls.append, "unexpected"))
            await asyncio.sleep(0)
            queued.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await queued
            self.assertEqual(calls, [])
        finally:
            released.set()
            await running
            await pool.aclose()
