# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect returned awaitable ownership during background worker cancellation."""

import asyncio
import inspect
import threading
import types
from contextlib import suppress
from typing import TYPE_CHECKING

from orionis.background import BackgroundTask
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Generator


async def _native_result() -> None:
    """Provide a native coroutine whose lifecycle can be inspected.

    Returns
    -------
    None
        No return value.
    """


@types.coroutine
def _legacy_result() -> Generator[None]:
    """Provide a generator-based coroutine for the cancellation boundary.

    Yields
    ------
    None
        Cooperative coroutine checkpoint.
    """
    yield


class TestBackgroundCancellation(TestCase):
    """Verify result cleanup after a cancelled task drains its worker."""

    async def testCancelledWorkerReleasesReturnedAwaitables(self) -> None:
        """Close or cancel awaitables returned by a cancelled background worker.

        Returns
        -------
        None
            No return value.
        """
        loop = asyncio.get_running_loop()
        for kind in ("coroutine", "generator", "future"):
            with self.subTest(kind=kind):
                started = asyncio.Event()
                release = threading.Event()
                if kind == "coroutine":
                    result = _native_result()
                elif kind == "generator":
                    result = _legacy_result()
                else:
                    result = loop.create_future()

                def work(
                    value: object = result,
                    entered: asyncio.Event = started,
                    gate: threading.Event = release,
                ) -> object:
                    """Return the selected awaitable after cancellation.

                    Parameters
                    ----------
                    value : object
                        Awaitable selected by the current scenario.
                    entered : asyncio.Event
                        Notification for the scenario's worker start.
                    gate : threading.Event
                        Release gate retained for this scenario.

                    Returns
                    -------
                    object
                        Result awaiting cleanup when the worker finishes.
                    """
                    loop.call_soon_threadsafe(entered.set)
                    gate.wait()
                    return value

                task = asyncio.create_task(BackgroundTask(work)())
                try:
                    await asyncio.wait_for(started.wait(), timeout=5)
                    task.cancel()
                    release.set()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                    if kind == "future":
                        self.assertTrue(result.cancelled())
                    elif kind == "coroutine":
                        self.assertEqual(
                            inspect.getcoroutinestate(result),
                            inspect.CORO_CLOSED,
                        )
                    else:
                        self.assertEqual(
                            inspect.getgeneratorstate(result),
                            inspect.GEN_CLOSED,
                        )
                finally:
                    release.set()
                    if not task.done():
                        task.cancel()
                        with suppress(asyncio.CancelledError):
                            await task
                    if kind == "future":
                        result.cancel()
                    else:
                        result.close()
