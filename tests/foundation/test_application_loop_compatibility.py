import asyncio
import contextvars
import gc
import warnings
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from tests.foundation.test_application_async import (
    _AsyncCall,
    _AsyncGate,
    _ReceiveChannel,
    _new_application,
)

class _TaskRecorder:
    """Implement a task factory that does not accept an eager-start argument."""

    def __init__(self) -> None:
        """Initialize the list of tasks created through the factory.

        Returns
        -------
        None
            The task record starts empty.
        """
        self.tasks = []

    def __call__(self, loop, coroutine, *, name=None, context=None) -> asyncio.Task:
        """Create a task using the documented factory arguments.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            Event loop owning the task.
        coroutine : Coroutine
            Coroutine scheduled by the application.
        name : str | None, optional
            Optional task name.
        context : contextvars.Context | None, optional
            Context copied or supplied by the caller.

        Returns
        -------
        asyncio.Task
            Task recorded for completion and coroutine-lifetime assertions.
        """
        task = asyncio.Task(coroutine, loop=loop, name=name, context=context)
        self.tasks.append(task)
        return task

class _AlternateLoop:
    """Expose the task-creation signature used by alternate event loops."""

    def __init__(self, loop) -> None:
        """Bind the task scheduler to the actual running loop.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            Loop that executes the simulated loop's tasks.

        Returns
        -------
        None
            The adapter starts with an empty task record.
        """
        self.loop = loop
        self.tasks = []

    def createTask(self, coroutine, *, name=None, context=None) -> asyncio.Task:
        """Schedule a coroutine without accepting an eager-start keyword.

        Parameters
        ----------
        coroutine : Coroutine
            Coroutine scheduled by the application.
        name : str | None, optional
            Optional task name.
        context : contextvars.Context | None, optional
            Context supplied by the caller.

        Returns
        -------
        asyncio.Task
            Task bound to the real running loop.
        """
        task = self.loop.create_task(coroutine, name=name, context=context)
        self.tasks.append(task)
        return task

    # Expose the event-loop protocol name through the camelCase implementation.
    create_task = createTask

class TestApplicationLoopCompatibility(IsolatedAsyncioTestCase):
    """Check monitored request lifetimes without requiring native eager support."""

    async def _exerciseLifecycle(
        self, mode: str, interface: str, outcome: str,
    ) -> None:
        """Run one monitored request through a selected scheduler and outcome.

        Parameters
        ----------
        mode : str
            Custom factory or alternate-loop scheduling mode.
        interface : str
            ASGI or RSGI transport under observation.
        outcome : str
            Normal completion, external cancellation, or client disconnect.

        Returns
        -------
        None
            Tasks complete, contexts stay isolated, and coroutines are closed.
        """
        loop = asyncio.get_running_loop()
        previous_factory = loop.get_task_factory()
        scheduler = _TaskRecorder() if mode == "factory" else _AlternateLoop(loop)
        application = _new_application()
        gate = _AsyncGate()
        channel = _ReceiveChannel()
        request_context = contextvars.ContextVar("loop-compatibility", default="server")

        async def handle(*arguments: object) -> str:
            """Check the inherited context and execute the suspended handler.

            Parameters
            ----------
            *arguments : object
                Original protocol arguments passed by Application.

            Returns
            -------
            str
                Handler result after normal completion.
            """
            self.assertEqual(request_context.get(), "server")
            request_context.set("handler")
            return await gate.run(*arguments)

        setattr(application, f"_Application__kernel_http_{interface}", handle)
        request = (
            application({"type": "http"}, channel.receive, _AsyncCall())
            if interface == "asgi" else
            application.__rsgi__(
                SimpleNamespace(proto="http"),
                SimpleNamespace(client_disconnect=channel.receive),
            )
        )
        with warnings.catch_warnings(record=True) as recorded, ExitStack() as stack:
            warnings.simplefilter("always", RuntimeWarning)
            if mode == "factory":
                loop.set_task_factory(scheduler)
            else:
                stack.enter_context(patch(
                    "orionis.foundation.application.asyncio.get_running_loop",
                    return_value=scheduler,
                ))
            task = asyncio.Task(request, loop=loop)
            try:
                async with asyncio.timeout(2):
                    await gate.entered.wait()
                    await channel.entered.wait()
                    if outcome == "cancel":
                        task.cancel()
                        with self.assertRaises(asyncio.CancelledError):
                            await task
                    elif outcome == "disconnect":
                        channel.messages.put_nowait({"type": "http.disconnect"})
                        self.assertIsNone(await task)
                    else:
                        gate.release.set()
                        self.assertEqual(await task, "response")
            finally:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                loop.set_task_factory(previous_factory)
            gc.collect()

        self.assertEqual(request_context.get(), "server")
        self.assertTrue(gate.cleaned.is_set())
        if outcome != "disconnect":
            self.assertTrue(channel.cleaned.is_set())
        self.assertEqual(len(scheduler.tasks), 2)
        self.assertTrue(all(child.done() for child in scheduler.tasks))
        self.assertTrue(all(
            child.get_coro().cr_frame is None for child in scheduler.tasks
        ))
        self.assertFalse([
            warning for warning in recorded
            if "was never awaited" in str(warning.message)
        ])

    async def testCustomFactoryAsgiLifecycle(self) -> None:
        """Preserve ASGI lifetime behavior with a factory lacking eager support.

        Returns
        -------
        None
            Completion, server cancellation, and disconnect finish cleanly.
        """
        for outcome in ("complete", "cancel", "disconnect"):
            with self.subTest(outcome=outcome):
                await self._exerciseLifecycle("factory", "asgi", outcome)

    async def testCustomFactoryRsgiLifecycle(self) -> None:
        """Preserve RSGI lifetime behavior with a factory lacking eager support.

        Returns
        -------
        None
            Completion, server cancellation, and disconnect finish cleanly.
        """
        for outcome in ("complete", "cancel", "disconnect"):
            with self.subTest(outcome=outcome):
                await self._exerciseLifecycle("factory", "rsgi", outcome)

    async def testAlternateLoopAsgiLifecycle(self) -> None:
        """Preserve ASGI lifetime behavior with an alternate task-creation API.

        Returns
        -------
        None
            Completion, server cancellation, and disconnect finish cleanly.
        """
        for outcome in ("complete", "cancel", "disconnect"):
            with self.subTest(outcome=outcome):
                await self._exerciseLifecycle("alternate", "asgi", outcome)

    async def testAlternateLoopRsgiLifecycle(self) -> None:
        """Preserve RSGI lifetime behavior with an alternate task-creation API.

        Returns
        -------
        None
            Completion, server cancellation, and disconnect finish cleanly.
        """
        for outcome in ("complete", "cancel", "disconnect"):
            with self.subTest(outcome=outcome):
                await self._exerciseLifecycle("alternate", "rsgi", outcome)
