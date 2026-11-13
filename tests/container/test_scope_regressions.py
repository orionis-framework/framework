# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect scoped publication from stale asynchronous completions."""

import asyncio
import inspect
from typing import get_type_hints

from orionis.container.context.manager import ScopeManager
from orionis.test import TestCase


async def _build_value(entered: asyncio.Event, release: asyncio.Event) -> str:
    """Return the old value after the scope has changed.

    Parameters
    ----------
    entered : asyncio.Event
        Signal that the stored coroutine has started.
    release : asyncio.Event
        Wait until the scope's stored value has been changed.

    Returns
    -------
    str
        Value belonging to the original stored coroutine.
    """
    entered.set()
    await release.wait()
    return "original"


class TestScopeRegressions(TestCase):
    """Exercise scope state while a stored coroutine is still running."""

    async def testPreservesChangesMadeWhileAValueIsResolving(self) -> None:
        """Keep a replacement or clear operation after an older value finishes."""
        for replacement in (False, True):
            with self.subTest(replacement=replacement):
                entered = asyncio.Event()
                release = asyncio.Event()

                async with ScopeManager() as scope:
                    scope.set("value", _build_value(entered, release))
                    pending = asyncio.create_task(scope.get("value"))
                    try:
                        await asyncio.wait_for(entered.wait(), timeout=2)
                        if replacement:
                            scope.set("value", "replacement")
                        else:
                            scope.clear()
                    finally:
                        release.set()
                        value = await asyncio.wait_for(pending, timeout=2)
                    self.assertEqual(value, "original")
                    if replacement:
                        self.assertEqual(await scope.get("value"), "replacement")
                    else:
                        self.assertNotIn("value", scope)

    def testResolvesScopeExitAnnotations(self) -> None:
        """Expose complete runtime annotations for the context manager protocol."""
        hints = get_type_hints(ScopeManager.__aexit__)
        self.assertIn("exc_tb", hints)

    async def testClosesUnstartedCoroutinesWhenDiscarded(self) -> None:
        """Release unstarted coroutine frames on replace, clear, and scope exit."""
        for operation in ("replace", "clear", "exit"):
            with self.subTest(operation=operation):
                pending = _build_value(asyncio.Event(), asyncio.Event())
                scope = ScopeManager()
                try:
                    await scope.__aenter__()
                    scope.set("value", pending)
                    scope.set("value", pending)
                    self.assertEqual(
                        inspect.getcoroutinestate(pending),
                        inspect.CORO_CREATED,
                    )
                    if operation == "replace":
                        scope.set("value", "replacement")
                    elif operation == "clear":
                        scope.clear()
                    else:
                        await scope.__aexit__(None, None, None)
                    self.assertEqual(
                        inspect.getcoroutinestate(pending),
                        inspect.CORO_CLOSED,
                    )
                finally:
                    if scope.isActive:
                        await scope.__aexit__(None, None, None)
                    pending.close()

    async def testLeavesRunningCoroutinesAndBorrowedTasksAlone(self) -> None:
        """Discard running work without taking over its caller-owned lifecycle."""
        for store_task in (False, True):
            with self.subTest(store_task=store_task):
                entered = asyncio.Event()
                release = asyncio.Event()
                coroutine = _build_value(entered, release)
                task = asyncio.create_task(coroutine)
                try:
                    await asyncio.wait_for(entered.wait(), timeout=2)
                    async with ScopeManager() as scope:
                        scope.set("value", task if store_task else coroutine)
                        scope.clear()
                    self.assertFalse(task.done())
                finally:
                    release.set()
                    result = await asyncio.wait_for(task, timeout=2)
                self.assertEqual(result, "original")
