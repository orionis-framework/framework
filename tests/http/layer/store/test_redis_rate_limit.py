import asyncio
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from orionis.foundation.config.http import HTTPRateLimit, Redis
from orionis.http.layer.store.redis_rate_limit import RedisRateLimitStore
from orionis.test import TestCase

class _RedisTransport:
    """Record script calls and simulate storage failure or cancellation."""

    __slots__ = ("calls", "closed", "error", "pending", "result")

    def __init__(self) -> None:
        """Initialize successful transport behavior.

        Returns
        -------
        None
            Prepare the script recorder and transport state.
        """
        self.calls = []
        self.closed = False
        self.error = None
        self.pending = False
        self.result = 1

    async def eval(self, *args: object) -> int:
        """Record one script command and return its configured result.

        Parameters
        ----------
        *args : object
            Script command and arguments supplied by the store.

        Returns
        -------
        int
            Configured result for the simulated script call.

        Raises
        ------
        Exception
            Propagate the configured transport error.
        """
        self.calls.append(args)
        if self.error:
            raise self.error
        if self.pending:
            await asyncio.Event().wait()
        return self.result

    async def aclose(self) -> None:
        """Record whether the store closes this transport.

        Returns
        -------
        None
            Mark the transport as closed.
        """
        self.closed = True

class TestRedisRateLimitStore(TestCase):
    """Verify command boundaries and resource ownership using explicit doubles."""

    async def testBuildsLazyClientFromConnectionFields(self) -> None:
        """Pass IPv6 and literal credentials directly to the real Redis client.

        Returns
        -------
        None
            Verify connection arguments and that construction opens no sockets.
        """
        credential = "test@credential:/?#%"
        config = HTTPRateLimit(
            rate_limit_redis=Redis(
                endpoint="::1", port=6381, db=4, password=credential,
            ),
            rate_limit_redis_timeout_seconds=2,
        )
        store = RedisRateLimitStore(config)
        try:
            pool = store._RedisRateLimitStore__client.connection_pool
            options = pool.connection_kwargs
            self.assertEqual(options["host"], "::1")
            self.assertEqual(options["port"], 6381)
            self.assertEqual(options["db"], 4)
            self.assertEqual(options["password"], credential)
            self.assertEqual(options["socket_connect_timeout"], 2)
            self.assertEqual(options["socket_timeout"], 2)
            self.assertEqual(pool.max_connections, 100)
            self.assertFalse(pool._available_connections)
            self.assertFalse(pool._in_use_connections)
        finally:
            await store.close()

    async def testUsesOneAtomicScriptWithUniqueMembersAndHashedIdentity(self) -> None:
        """Send distinct attempt IDs without exposing client IP addresses.

        Returns
        -------
        None
            Verify each quota check uses one atomic script and hashed identity.
        """
        transport = _RedisTransport()
        store = RedisRateLimitStore(HTTPRateLimit(), client=transport)
        self.assertTrue(await store.hit("192.0.2.1", 3, 60))
        self.assertTrue(await store.hit("192.0.2.1", 3, 60))
        first, second = transport.calls
        self.assertEqual(first[1], 1)
        self.assertEqual(first[2], second[2])
        self.assertNotIn("192.0.2.1", first[2])
        self.assertEqual(first[3:5], (3, 60))
        self.assertNotEqual(first[5], second[5])

    async def testRejectsQuotaAndPropagatesStorageFailure(self) -> None:
        """Preserve Redis rejection and storage errors for middleware.

        Returns
        -------
        None
            Verify denied attempts and backend failures remain distinguishable.
        """
        transport = _RedisTransport()
        transport.result = 0
        store = RedisRateLimitStore(HTTPRateLimit(), client=transport)
        self.assertFalse(await store.hit("client", 1, 60))
        transport.error = RedisConnectionError()
        with self.assertRaises(RedisConnectionError):
            await store.hit("client", 1, 60)

    async def testCancellationIsNeverConvertedToQuotaOrStorageFailure(self) -> None:
        """Allow server cancellation to unwind pending Redis requests.

        Returns
        -------
        None
            Verify cancellation propagates from a pending script call.
        """
        transport = _RedisTransport()
        transport.pending = True
        store = RedisRateLimitStore(HTTPRateLimit(), client=transport)
        task = asyncio.create_task(store.hit("client", 1, 60))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def testWholeOperationTimeoutRejectsPendingRedisCall(self) -> None:
        """Bound the complete call when the transport never replies.

        Returns
        -------
        None
            Verify a pending script call is limited by the configured timeout.
        """
        transport = _RedisTransport()
        transport.pending = True
        store = RedisRateLimitStore(HTTPRateLimit(), client=transport)
        store._RedisRateLimitStore__timeout = 0.01
        with self.assertRaises(RedisTimeoutError):
            await asyncio.wait_for(store.hit("client", 1, 60), timeout=1)
        self.assertEqual(len(transport.calls), 1)

    async def testExternalClientRemainsOwnedByCaller(self) -> None:
        """Leave an injected shared connection pool owned by its caller.

        Returns
        -------
        None
            Verify closing the store does not close an external client.
        """
        transport = _RedisTransport()
        store = RedisRateLimitStore(HTTPRateLimit(), client=transport)
        await store.close()
        self.assertFalse(transport.closed)

    async def testOwnedClientIsClosedWithoutDeletingQuotas(self) -> None:
        """Close the owned client pool without connecting to Redis.

        Returns
        -------
        None
            Verify shutdown closes the pool without issuing quota commands.
        """
        store = RedisRateLimitStore(HTTPRateLimit())
        transport = _RedisTransport()
        store._RedisRateLimitStore__client = transport
        await store.close()
        self.assertTrue(transport.closed)
        self.assertFalse(transport.calls)

    async def testZeroQuotaSkipsStorage(self) -> None:
        """Avoid network writes when no attempt can be admitted.

        Returns
        -------
        None
            Verify a zero quota returns rejection without a script call.
        """
        transport = _RedisTransport()
        store = RedisRateLimitStore(HTTPRateLimit(), client=transport)
        self.assertFalse(await store.hit("client", 0, 60))
        self.assertFalse(transport.calls)
