"""Protect one incident's deferred effects across reentrant owners."""

import asyncio
from unittest.mock import AsyncMock
from orionis.failure.entities.handling import FailureHandling
from orionis.test import TestCase


class TestFailureHandling(TestCase):
    """Verify that completing and presenting plans never repeats effects."""

    async def testConcurrentCompletionLogsOnce(self) -> None:
        """Every waiter sees the same completed logging effect."""
        entered = asyncio.Event()
        release = asyncio.Event()

        async def write():
            entered.set()
            await release.wait()

        logging = AsyncMock(side_effect=write)
        handling = FailureHandling(logging=logging)
        first = asyncio.create_task(handling.complete())
        await entered.wait()
        second = asyncio.create_task(handling.complete())
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        release.set()
        await asyncio.gather(first, second)
        await handling.complete()
        logging.assert_awaited_once()
        self.assertTrue(handling.reported)

    async def testConcurrentPresentationReusesOriginalResponse(self) -> None:
        """Only the protocol owner that presents first supplies live state."""
        response = object()
        presentation = AsyncMock(return_value=response)
        handling = FailureHandling(presentation=presentation)
        request = object()
        results = await asyncio.gather(*(
            handling.present(flow="http", request=request) for _ in range(8)
        ))
        self.assertTrue(all(result is response for result in results))
        presentation.assert_awaited_once_with(flow="http", request=request)

    async def testFailedLoggingCanStillPresentAndCannotRetry(self) -> None:
        """A logging error remains stable while HTTP presentation is usable."""
        error = OSError("logger")
        logging = AsyncMock(side_effect=error)
        response = object()
        presentation = AsyncMock(return_value=response)
        handling = FailureHandling(logging=logging, presentation=presentation)
        for _ in range(2):
            with self.assertRaises(OSError) as raised:
                await handling.complete()
            self.assertIs(raised.exception, error)
        self.assertIs(await handling.present(flow="http"), response)
        logging.assert_awaited_once()
        self.assertFalse(handling.reported)

    async def testCancelledLoggingIsNotExecutedAgain(self) -> None:
        """Cancellation propagates without retrying possibly partial logging."""
        entered = asyncio.Event()

        async def write():
            entered.set()
            await asyncio.Event().wait()

        logging = AsyncMock(side_effect=write)
        handling = FailureHandling(logging=logging)
        task = asyncio.create_task(handling.complete())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        with self.assertRaises(asyncio.CancelledError):
            await handling.complete()
        logging.assert_awaited_once()

    async def testEmptyPlanHasNoEffects(self) -> None:
        """Ignored failures can complete without logging or presentation."""
        handling = FailureHandling()
        await handling.complete()
        self.assertIsNone(await handling.present(flow="cli"))
        self.assertFalse(handling.reported)


    async def testCancellingACompletionWaiterDoesNotCancelTheOwner(self) -> None:
        """A waiting caller can leave without interrupting or repeating logging."""
        entered = asyncio.Event()
        release = asyncio.Event()

        async def write():
            entered.set()
            await release.wait()

        logging = AsyncMock(side_effect=write)
        handling = FailureHandling(logging=logging)
        owner = asyncio.create_task(handling.complete())
        await entered.wait()
        waiter = asyncio.create_task(handling.complete())
        try:
            await asyncio.sleep(0)
            waiter.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await waiter
            self.assertFalse(owner.done())
            release.set()
            await owner
            await handling.complete()
        finally:
            release.set()
            await asyncio.gather(owner, waiter, return_exceptions=True)
        logging.assert_awaited_once()
        self.assertTrue(handling.reported)

    async def testFailedPresentationCachesTheOriginalError(self) -> None:
        """Presentation errors, including internal cancellation, cannot rerun output."""
        for error in (OSError("presentation"), asyncio.CancelledError()):
            with self.subTest(error=type(error)):
                presentation = AsyncMock(side_effect=error)
                handling = FailureHandling(presentation=presentation)
                for _ in range(2):
                    with self.assertRaises(type(error)) as raised:
                        await handling.present(flow="http")
                    self.assertIs(raised.exception, error)
                presentation.assert_awaited_once_with(flow="http", request=None)
