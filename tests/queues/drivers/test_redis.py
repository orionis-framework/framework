from typing import TYPE_CHECKING
from redis.exceptions import RedisError
from orionis.foundation.config.queue import Redis as RedisConfig
from orionis.queues.drivers.redis import RedisQueueDriver
from orionis.queues.exceptions import QueueConfigurationError, QueueStorageError
from orionis.test import TestCase
from tests.queues.drivers.test_database import make_envelope

if TYPE_CHECKING:
    from orionis.queues.entities.reserved_job import ReservedJob


class _RedisTransport:
    """Provide explicit replies and capture atomic Redis transport calls."""

    __slots__ = ("calls", "closed", "error", "replies", "size_value")

    def __init__(self) -> None:
        """Initialize a transport fake with explicit controllable state.

        Returns
        -------
        None
            Prepare captured calls and queued replies.
        """
        self.calls: list[tuple[str, int, tuple[object, ...]]] = []
        self.replies: list[object] = []
        self.error: RedisError | None = None
        self.size_value = 0
        self.closed = False

    async def eval(self, script: str, numkeys: int, *values: object) -> object:
        """Capture one script invocation and return its explicitly queued reply.

        Parameters
        ----------
        script : str
            Lua source provided by the driver.
        numkeys : int
            Number of keys preceding bound arguments.
        *values : object
            Supplied keys and arguments.

        Returns
        -------
        object
            Next test reply.
        """
        self.calls.append((script, numkeys, values))
        if self.error is not None:
            raise self.error
        return self.replies.pop(0)

    async def hlen(self, key: str) -> int:
        """Capture a hash-size request and return its explicit count.

        Parameters
        ----------
        key : str
            Payload hash whose jobs are counted.

        Returns
        -------
        int
            Test-controlled persisted job count.
        """
        self.calls.append(("HLEN", 1, (key,)))
        if self.error is not None:
            raise self.error
        return self.size_value

    async def aclose(self) -> None:
        """Record a request to close the transport.

        Returns
        -------
        None
            Mark the explicit fake as closed.
        """
        self.closed = True


class TestRedisQueueDriverTransport(TestCase):
    """Verify driver transport and result validation without a Redis server."""

    __slots__ = ("_driver", "_transport")

    async def asyncSetUp(self) -> None:
        """Create an injected transport with no network connections.

        Returns
        -------
        None
            Bind the driver to an explicit transport fake.
        """
        self._transport = _RedisTransport()
        self._driver = RedisQueueDriver(
            RedisConfig(prefix="test:queues"), client=self._transport,
        )

    async def _reserve(self) -> ReservedJob:
        """Prepare and reserve an envelope using a valid transport reply.

        Returns
        -------
        ReservedJob
            Reservation reconstructed from a Redis response.
        """
        envelope = make_envelope("high")
        self._transport.replies.append([envelope.id.encode(), b"envelope", 2])
        return await self._driver.reserve(("high",), 60.0)

    async def testPushUsesOneAtomicScriptAndColocatedKeys(self) -> None:
        """Submit payload and availability in one atomic script call.

        Returns
        -------
        None
            Assert namespace, hash tags, script arguments, and stable id.
        """
        envelope = make_envelope("high")
        self._transport.replies.append(1)
        self.assertEqual(await self._driver.push(envelope, delay=5), envelope.id)
        script, key_count, values = self._transport.calls[0]
        self.assertEqual(key_count, 5)
        self.assertTrue(all("{high}" in key for key in values[:key_count]))
        self.assertEqual(values[0], "test:queues:{high}:ready")
        self.assertEqual(values[key_count], envelope.id)
        self.assertIsInstance(values[key_count + 1], bytes)
        self.assertIn("HEXISTS", script)
        self.assertEqual(len(self._transport.calls), 1)

    async def testReserveRespectsPriorityAndReconstructsClaim(self) -> None:
        """Try queues in priority order and preserve claim metadata.

        Returns
        -------
        None
            Assert first nonempty queue and returned attempt state.
        """
        envelope = make_envelope()
        self._transport.replies.extend([[], [envelope.id.encode(), b"wire", 4]])
        reserved = await self._driver.reserve(("high", "default"), 60.0)
        self.assertEqual(reserved.id, envelope.id)
        self.assertEqual(reserved.queue, "default")
        self.assertEqual(reserved.payload, b"wire")
        self.assertEqual(reserved.attempts, 4)
        self.assertEqual(len(reserved.token), 32)
        self.assertEqual(len(self._transport.calls), 2)
        self.assertIn("{high}", self._transport.calls[0][2][0])
        self.assertIn("{default}", self._transport.calls[1][2][0])

    async def testReserveReturnsNoneWhenAllQueuesEmpty(self) -> None:
        """Return no reservation when every priority queue is empty.

        Returns
        -------
        None
            Assert no fabricated reservation is returned.
        """
        self._transport.replies.extend([[], []])
        self.assertIsNone(await self._driver.reserve(("high", "default"), 60.0))

    async def testMalformedRepliesFailExplicitly(self) -> None:
        """Reject malformed claim replies without silently treating them as empty.

        Returns
        -------
        None
            Assert invalid result shape and identifiers fail explicitly.
        """
        for reply in (
            None, [b"id"], [b"id", "payload", 1], [b"id", b"wire", 0],
            [b"id", b"wire", "1"], [b"\xff", b"wire", 1],
        ):
            self._transport.replies.append(reply)
            with self.assertRaises(QueueStorageError):
                await self._driver.reserve(("default",), 60.0)

    async def testReleaseAndDeleteCarryFencingToken(self) -> None:
        """Bind reservation identifiers and tokens to ownership transitions.

        Returns
        -------
        None
            Assert stale replies remain false and current transitions succeed.
        """
        reserved = await self._reserve()
        self._transport.replies.extend([1, 0, 1, 0])
        self.assertTrue(await self._driver.release(reserved, delay=5))
        self.assertFalse(await self._driver.release(reserved))
        self.assertTrue(await self._driver.delete(reserved))
        self.assertFalse(await self._driver.delete(reserved))
        for script, key_count, values in self._transport.calls[1:]:
            self.assertEqual(values[key_count], reserved.id)
            self.assertEqual(values[key_count + 1], reserved.token)
            self.assertIn("tonumber(lease)", script)

    async def testSizeAndClearReportAllPersistedJobs(self) -> None:
        """Count and clear complete queue state through their transport contracts.

        Returns
        -------
        None
            Assert size and atomic clear result handling.
        """
        self._transport.size_value = 7
        self.assertEqual(await self._driver.size("default"), 7)
        self._transport.replies.append(7)
        self.assertEqual(await self._driver.clear("default"), 7)
        self.assertIn("unpack(KEYS)", self._transport.calls[-1][0])

    async def testTranslateRedisErrorsPreservingCause(self) -> None:
        """Translate transport failures while retaining their original cause.

        Returns
        -------
        None
            Assert Redis diagnostics remain available through exception chaining.
        """
        self._transport.error = RedisError("transport unavailable")
        with self.assertRaises(QueueStorageError) as raised:
            await self._driver.push(make_envelope())
        self.assertIs(raised.exception.__cause__, self._transport.error)
        with self.assertRaises(QueueStorageError):
            await self._driver.size("default")

    async def testRejectDuplicateIdentifier(self) -> None:
        """Reject Redis's duplicate-id response without mutating the envelope.

        Returns
        -------
        None
            Assert duplicate pushes fail explicitly.
        """
        self._transport.replies.append(0)
        with self.assertRaises(QueueStorageError):
            await self._driver.push(make_envelope())

    async def testCloseLeavesInjectedTransportOwnedByCaller(self) -> None:
        """Preserve caller ownership of an explicitly injected Redis transport.

        Returns
        -------
        None
            Assert external clients are not closed by the driver.
        """
        await self._driver.close()
        self.assertFalse(self._transport.closed)

    async def testRejectInvalidQueueAndPrefix(self) -> None:
        """Reject invalid queue names and Redis key namespaces.

        Returns
        -------
        None
            Assert invalid names fail before script execution.
        """
        with self.assertRaises(QueueConfigurationError):
            await self._driver.reserve(("bad{queue}",), 60.0)
        with self.assertRaises(QueueStorageError):
            RedisQueueDriver(
                RedisConfig(prefix="bad{prefix}"), client=self._transport,
            )
        self.assertEqual(self._transport.calls, [])
