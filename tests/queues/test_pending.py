import asyncio
from typing import TYPE_CHECKING
from orionis.queues.exceptions import QueueConfigurationError, QueueDispatchError
from orionis.queues.pending import PendingDispatch
from orionis.test import TestCase
from tests.queues.test_serializer import StateJob

if TYPE_CHECKING:
    from orionis.queues.job import BaseJob


class DispatchRecorder:
    """Record awaited submissions without opening a backend."""

    __slots__ = ("calls", "release", "started")

    def __init__(self) -> None:
        """Create deterministic submission synchronization.

        Returns
        -------
        None
            Initialize recording and task events.
        """
        self.calls: list[tuple[BaseJob, str | None, str | None, float]] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def submit(
        self, job: BaseJob, connection: str | None, queue: str | None, delay: float,
    ) -> str:
        """Record one submission and wait for explicit completion.

        Parameters
        ----------
        job : BaseJob
            Instance to dispatch.
        connection : str | None
            Selected backend.
        queue : str | None
            Selected channel.
        delay : float
            Relative availability delay.

        Returns
        -------
        str
            Test job identifier.
        """
        self.calls.append((job, connection, queue, delay))
        self.started.set()
        await self.release.wait()
        return "job-id"


async def await_pending(pending: PendingDispatch) -> str:
    """Await one pending operation from an independent caller task.

    Parameters
    ----------
    pending : PendingDispatch
        Operation to join.

    Returns
    -------
    str
        Result returned by dispatch.
    """
    return await pending


class TestPendingDispatch(TestCase):
    async def testDeferredFluentSelectionAndRepeatedAwait(self) -> None:
        """Submit once after fluent selection even with concurrent awaiters.

        Returns
        -------
        None
            Verify dispatch remains deferred and stores the chosen options.
        """
        recorder = DispatchRecorder()
        job = StateJob(1, None)
        pending = PendingDispatch(recorder.submit, job)
        pending.onConnection("redis").onQueue("emails").delay(seconds=0.5)
        self.assertEqual(recorder.calls, [])
        recorder.release.set()
        results = await asyncio.gather(await_pending(pending), await_pending(pending))
        self.assertEqual(results, ["job-id", "job-id"])
        self.assertEqual(recorder.calls, [(job, "redis", "emails", 0.5)])
        self.assertEqual(await pending, "job-id")
        with self.assertRaises(QueueDispatchError):
            pending.onQueue("changed")

    async def testCancelledFollowerDoesNotDuplicateSubmission(self) -> None:
        """Preserve submission when a following awaiting caller is cancelled.

        Returns
        -------
        None
            Verify another caller observes the original task's result.
        """
        recorder = DispatchRecorder()
        pending = PendingDispatch(recorder.submit, StateJob(1, None))
        initiator = asyncio.create_task(await_pending(pending))
        await recorder.started.wait()
        follower = asyncio.create_task(await_pending(pending))
        await asyncio.sleep(0)
        follower.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await follower
        recorder.release.set()
        self.assertEqual(await initiator, "job-id")
        self.assertEqual(await pending, "job-id")
        self.assertEqual(len(recorder.calls), 1)

    async def testInitiatorCancellationRemainsTerminal(self) -> None:
        """Preserve caller cancellation without restarting an uncertain push.

        Returns
        -------
        None
            Verify cancelled dispatches never perform an implicit second push.
        """
        recorder = DispatchRecorder()
        pending = PendingDispatch(recorder.submit, StateJob(1, None))
        initiator = asyncio.create_task(await_pending(pending))
        await recorder.started.wait()
        initiator.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await initiator
        with self.assertRaises(asyncio.CancelledError):
            await pending
        self.assertEqual(len(recorder.calls), 1)

    def testRejectInvalidOptions(self) -> None:
        """Reject unsafe names and invalid relative delays before submission.

        Returns
        -------
        None
            Verify immediate fluent option validation.
        """
        pending = PendingDispatch(DispatchRecorder().submit, StateJob(1, None))
        for name in ("", "emails:ready", "../jobs", "space name"):
            with self.subTest(name=name), self.assertRaises(QueueConfigurationError):
                pending.onQueue(name)
        for delay in (-1, True, float("nan"), float("inf")):
            with self.subTest(delay=delay), self.assertRaises(QueueConfigurationError):
                pending.delay(delay)
