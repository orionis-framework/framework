import asyncio
import os
from typing import Self
from uuid import uuid4
import msgspec
from orionis.foundation.config.queue import Redis as RedisConfig
from orionis.queues.drivers import redis as redis_module
from orionis.queues.drivers.redis import RedisQueueDriver
from orionis.queues.exceptions import QueueStorageError
from orionis.test import TestCase
from tests.queues.drivers.test_database import (
    DurableDriverContract,
    _Clock,
    make_envelope,
)

class TestRedisQueueIntegration(DurableDriverContract, TestCase):
    """Run the durable contract explicitly against an isolated Redis server."""

    __slots__ = ("_clock", "_driver", "_settings")

    async def asyncSetUp(self: Self) -> None:
        """Require an explicit Redis host and isolate every test namespace.

        Returns
        -------
        None
            Prepare real Redis scripts without an external general-suite need.

        Raises
        ------
        SkipTest
            If the Redis integration host is not configured.
        """
        host = os.environ.get("ORIONIS_QUEUE_REDIS_HOST")
        if not host:
            self.skipTest(
                "Set ORIONIS_QUEUE_REDIS_HOST to run Redis integration tests.",
            )
        # Lua receives the caller's timestamp. Control that timestamp just as
        # the database contract does, without assuming network calls take <80 ms.
        self.addCleanup(
            setattr,
            redis_module,
            "current_time",
            redis_module.current_time,
        )
        self._clock = _Clock()
        redis_module.current_time = self._clock
        self._settings = RedisConfig(
            endpoint=host,
            port=int(os.environ.get("ORIONIS_QUEUE_REDIS_PORT", "6379")),
            db=int(os.environ.get("ORIONIS_QUEUE_REDIS_DB", "0")),
            password=os.environ.get("ORIONIS_QUEUE_REDIS_PASSWORD"),
            prefix=f"orionis:test:{uuid4().hex}",
        )
        self._driver = RedisQueueDriver(self._settings)

    async def _advanceTime(self: Self, seconds: float) -> None:
        """Advance lease deadlines independently of network or debug-loop latency.

        Parameters
        ----------
        seconds : float
            Duration added to the timestamp passed to Lua.

        Returns
        -------
        None
            Yield once after advancing the controlled clock.
        """
        self._clock.now += seconds
        await asyncio.sleep(0)

    async def asyncTearDown(self: Self) -> None:
        """Remove isolated queue namespaces and close Redis connections.

        Returns
        -------
        None
            Release all test-owned Redis state and connections.
        """
        for queue in ("default", "high", "other", "emails"):
            await self._driver.clear(queue)
        await self._driver.close()

    async def testPersistenceAcrossDriverRecreation(self: Self) -> None:
        """Retain queued state when recreating the Redis client and driver.

        Returns
        -------
        None
            Assert persisted attempts survive driver recreation.
        """
        envelope = make_envelope()
        await self._driver.push(envelope)
        reserved = await self._driver.reserve(("default",), 60.0)
        await self._driver.release(reserved)
        await self._driver.close()
        self._driver = RedisQueueDriver(self._settings)
        next_reservation = await self._driver.reserve(("default",), 60.0)
        self.assertEqual(next_reservation.id, envelope.id)
        self.assertEqual(next_reservation.attempts, 2)

    async def testCorruptAttemptsNeverRemoveReadyJob(self: Self) -> None:
        """Reject corrupt counters before removing any ready queue state.

        Returns
        -------
        None
            Assert a failed Lua increment preserves the envelope and readiness.
        """
        envelope = make_envelope()
        await self._driver.push(envelope)
        keys = self._driver._keys("default")
        await self._driver._client.hset(keys[3], envelope.id, b"not-an-integer")
        with self.assertRaises(QueueStorageError):
            await self._driver.reserve(("default",), 60.0)
        self.assertEqual(await self._driver.size("default"), 1)
        self.assertIsNotNone(await self._driver._client.zscore(keys[0], envelope.id))
        self.assertEqual(await self._driver._client.zcard(keys[1]), 0)
        await self._driver._client.hset(keys[3], envelope.id, 0)
        reserved = await self._driver.reserve(("default",), 60.0)
        self.assertEqual(reserved.attempts, 1)
        self.assertTrue(await self._driver.delete(reserved))

    async def testMissingPayloadNeverRemovesReadyJob(self: Self) -> None:
        """Preserve ready state when a stored envelope has been corrupted.

        Returns
        -------
        None
            Assert missing payload detection occurs before claiming the job.
        """
        envelope = make_envelope()
        await self._driver.push(envelope)
        keys = self._driver._keys("default")
        await self._driver._client.hdel(keys[2], envelope.id)
        with self.assertRaises(QueueStorageError):
            await self._driver.reserve(("default",), 60.0)
        self.assertIsNotNone(await self._driver._client.zscore(keys[0], envelope.id))
        self.assertEqual(await self._driver._client.zcard(keys[1]), 0)
        await self._driver._client.hset(
            keys[2],
            envelope.id,
            msgspec.json.encode(envelope),
        )
        self.assertEqual(
            (await self._driver.reserve(("default",), 60.0)).id,
            envelope.id,
        )

    async def testWrongKeyTypeNeverPartiallyPushes(self: Self) -> None:
        """Reject incorrect Redis key types before storing partial job state.

        Returns
        -------
        None
            Assert an invalid ready key cannot leave an orphan envelope.
        """
        envelope = make_envelope()
        keys = self._driver._keys("default")
        await self._driver._client.set(keys[0], b"corrupt")
        with self.assertRaises(QueueStorageError):
            await self._driver.push(envelope)
        self.assertEqual(await self._driver._client.hlen(keys[2]), 0)
        self.assertEqual(await self._driver._client.hlen(keys[3]), 0)

    async def testWrongReadyTypeNeverLosesReleasedReservation(self: Self) -> None:
        """Validate release destination types before removing an owned lease.

        Returns
        -------
        None
            Assert a release error preserves the reserved job and ownership.
        """
        envelope = make_envelope()
        await self._driver.push(envelope)
        reserved = await self._driver.reserve(("default",), 60.0)
        keys = self._driver._keys("default")
        await self._driver._client.set(keys[0], b"corrupt")
        with self.assertRaises(QueueStorageError):
            await self._driver.release(reserved)
        self.assertIsNotNone(await self._driver._client.zscore(keys[1], envelope.id))
        self.assertEqual(
            await self._driver._client.hget(keys[4], envelope.id),
            reserved.token.encode(),
        )
        self.assertEqual(await self._driver.size("default"), 1)
        await self._driver._client.delete(keys[0])
        self.assertTrue(await self._driver.release(reserved))
