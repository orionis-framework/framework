import asyncio
from uuid import uuid4
import msgspec
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.exceptions import QueueConfigurationError

def make_envelope(queue: str = "default") -> JobEnvelope:
    """Build a valid envelope for driver contract tests.

    Parameters
    ----------
    queue : str, optional
        Logical queue used by the test envelope.

    Returns
    -------
    JobEnvelope
        Unique envelope independent of application job registration.
    """
    return JobEnvelope(
        id=str(uuid4()), job="tests.queues.drivers.contract:ContractJob",
        payload=b"{}", connection="database", queue=queue,
        max_tries=3, timeout=1.0, backoff=(0.0,),
    )

class DurableDriverContract:
    """Exercise identical persistence and lease behavior for durable drivers."""

    __slots__ = ()

    async def _advanceTime(self, seconds: float) -> None:
        """Wait for a real backend deadline unless a controlled clock is used.

        Parameters
        ----------
        seconds : float
            Duration added to the backend's notion of current time.

        Returns
        -------
        None
            Make delayed work or leases eligible for the next assertion.
        """
        await asyncio.sleep(seconds)

    async def testPushReserveDelete(self) -> None:
        """Round-trip one envelope through a complete reservation.

        Returns
        -------
        None
            Assert stable payload, first attempt, and acknowledged removal.
        """
        envelope = make_envelope()
        self.assertEqual(await self._driver.push(envelope), envelope.id)
        reserved = await self._driver.reserve(("default",), 60.0)
        self.assertIsNotNone(reserved)
        self.assertEqual(reserved.id, envelope.id)
        self.assertEqual(reserved.attempts, 1)
        self.assertEqual(
            msgspec.json.decode(reserved.payload, type=JobEnvelope), envelope,
        )
        self.assertEqual(await self._driver.size("default"), 1)
        self.assertIsNone(await self._driver.reserve(("default",), 60.0))
        self.assertTrue(await self._driver.delete(reserved))
        self.assertFalse(await self._driver.delete(reserved))
        self.assertEqual(await self._driver.size("default"), 0)

    async def testDelayedJob(self) -> None:
        """Keep a delayed job unavailable until its deadline.

        Returns
        -------
        None
            Assert delayed visibility and eventual reservation.
        """
        envelope = make_envelope()
        await self._driver.push(envelope, delay=0.08)
        self.assertIsNone(await self._driver.reserve(("default",), 60.0))
        self.assertEqual(await self._driver.size("default"), 1)
        await self._advanceTime(0.12)
        self.assertEqual(
            (await self._driver.reserve(("default",), 60.0)).id, envelope.id,
        )

    async def testReleaseDelayAndAttempts(self) -> None:
        """Preserve attempts when releasing a job with delayed availability.

        Returns
        -------
        None
            Assert one increment per successful reservation.
        """
        await self._driver.push(make_envelope())
        reserved = await self._driver.reserve(("default",), 60.0)
        self.assertTrue(await self._driver.release(reserved, delay=0.08))
        self.assertFalse(await self._driver.release(reserved))
        self.assertIsNone(await self._driver.reserve(("default",), 60.0))
        await self._advanceTime(0.12)
        next_reservation = await self._driver.reserve(("default",), 60.0)
        self.assertEqual(next_reservation.attempts, 2)
        self.assertNotEqual(next_reservation.token, reserved.token)
        self.assertFalse(await self._driver.delete(reserved))
        self.assertTrue(await self._driver.delete(next_reservation))

    async def testExpiredLeaseRecoveryAndFencing(self) -> None:
        """Recover expired reservations while rejecting their stale owners.

        Returns
        -------
        None
            Assert fencing before and after another worker reclaims the job.
        """
        envelope = make_envelope()
        await self._driver.push(envelope)
        expired = await self._driver.reserve(("default",), 0.05)
        await self._advanceTime(0.08)
        self.assertFalse(await self._driver.delete(expired))
        self.assertFalse(await self._driver.release(expired))
        reserved = await self._driver.reserve(("default",), 60.0)
        self.assertEqual(reserved.id, envelope.id)
        self.assertEqual(reserved.attempts, 2)
        self.assertNotEqual(expired.token, reserved.token)
        self.assertFalse(await self._driver.delete(expired))
        self.assertFalse(await self._driver.release(expired))
        self.assertTrue(await self._driver.delete(reserved))

    async def testQueueIsolationAndPriority(self) -> None:
        """Consume multiple logical queues in explicit priority order.

        Returns
        -------
        None
            Assert isolation and higher-priority consumption.
        """
        low = make_envelope("default")
        high = make_envelope("high")
        await self._driver.push(low)
        await self._driver.push(high)
        self.assertIsNone(await self._driver.reserve(("emails",), 60.0))
        first = await self._driver.reserve(("high", "default"), 60.0)
        second = await self._driver.reserve(("high", "default"), 60.0)
        self.assertEqual(first.id, high.id)
        self.assertEqual(second.id, low.id)

    async def testClearFencesActiveReservations(self) -> None:
        """Remove ready, delayed, and reserved jobs only from the named queue.

        Returns
        -------
        None
            Assert clear counts and stale acknowledgements.
        """
        await self._driver.push(make_envelope())
        reserved = await self._driver.reserve(("default",), 60.0)
        await self._driver.push(make_envelope(), delay=60)
        await self._driver.push(make_envelope())
        await self._driver.push(make_envelope("other"))
        self.assertEqual(await self._driver.clear("default"), 3)
        self.assertEqual(await self._driver.clear("default"), 0)
        self.assertFalse(await self._driver.delete(reserved))
        self.assertEqual(await self._driver.size("default"), 0)
        self.assertEqual(await self._driver.size("other"), 1)

    async def testConcurrentClaimSingleWinner(self) -> None:
        """Grant exactly one of one hundred simultaneous reservation attempts.

        Returns
        -------
        None
            Assert single ownership repeatedly against a durable backend.
        """
        for _ in range(3):
            envelope = make_envelope()
            await self._driver.push(envelope)
            reservations = await asyncio.gather(*(
                self._driver.reserve(("default",), 60.0) for _ in range(100)
            ), return_exceptions=True)
            errors = [item for item in reservations if isinstance(item, BaseException)]
            self.assertEqual(errors, [])
            winners = [item for item in reservations if item is not None]
            self.assertEqual(len(winners), 1)
            self.assertEqual(winners[0].id, envelope.id)
            self.assertEqual(winners[0].attempts, 1)
            self.assertTrue(await self._driver.delete(winners[0]))

    async def _consumeJobs(self) -> list[str]:
        """Reserve and acknowledge jobs until the backend has no ready work.

        Returns
        -------
        list of str
            Identifiers processed by this consumer.
        """
        processed = []
        while (reserved := await self._driver.reserve(("default",), 60.0)):
            processed.append(reserved.id)
            self.assertTrue(await self._driver.delete(reserved))
        return processed

    async def testManyJobsManyWorkers(self) -> None:
        """Process every job without loss across many competing consumers.

        Returns
        -------
        None
            Assert complete, unique acknowledged processing.
        """
        envelopes = [make_envelope() for _ in range(40)]
        for envelope in envelopes:
            await self._driver.push(envelope)
        async with asyncio.TaskGroup() as group:
            consumers = [group.create_task(self._consumeJobs()) for _ in range(20)]
        results = [task.result() for task in consumers]
        processed = [job_id for group in results for job_id in group]
        self.assertEqual(len(processed), len(envelopes))
        self.assertEqual(set(processed), {item.id for item in envelopes})
        self.assertEqual(await self._driver.size("default"), 0)

    async def testRejectInvalidDurations(self) -> None:
        """Reject invalid persistence and lease durations before writing jobs.

        Returns
        -------
        None
            Assert negative delays and nonpositive leases fail explicitly.
        """
        with self.assertRaises(QueueConfigurationError):
            await self._driver.push(make_envelope(), delay=-1)
        with self.assertRaises(QueueConfigurationError):
            await self._driver.reserve(("default",), 0)
        self.assertEqual(await self._driver.size("default"), 0)
