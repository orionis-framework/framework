import asyncio
import multiprocessing
import os
from hashlib import sha256
from uuid import uuid4
from redis.exceptions import ResponseError
from orionis.foundation.config.http import HTTPRateLimit
from orionis.http.layer.store.redis_rate_limit import RedisRateLimitStore
from orionis.test import TestCase

def _process_hits(url: str, prefix: str, output: object) -> None:
    """Count accepted requests from an independent process.

    Parameters
    ----------
    url : str
        Redis connection URL.
    prefix : str
        Isolated key namespace for the integration run.
    output : object
        Queue that receives the accepted-request count.

    Returns
    -------
    None
        Place the worker's accepted-request count on the output queue.
    """
    async def run() -> int:
        """Use and close an independent Redis connection pool.

        Returns
        -------
        int
            Number of requests accepted by this worker.
        """
        store = RedisRateLimitStore(HTTPRateLimit(
            rate_limit_redis_url=url, rate_limit_redis_prefix=prefix,
        ))
        try:
            return sum([await store.hit("process-client", 17, 60)
                        for _ in range(50)])
        finally:
            await store.close()

    output.put(asyncio.run(run()))

def _run_processes(url: str, prefix: str) -> list[int]:
    """Spawn isolated workers and collect their accepted-request counts.

    Parameters
    ----------
    url : str
        Redis connection URL shared by the workers.
    prefix : str
        Isolated key namespace for the integration run.

    Returns
    -------
    list[int]
        Accepted-request count reported by each worker.
    """
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    processes = [context.Process(target=_process_hits, args=(url, prefix, output))
                 for _ in range(3)]
    try:
        for process in processes:
            process.start()
        results = [output.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=10)
            if process.exitcode != 0:
                error_msg = "Rate-limit integration worker failed."
                raise RuntimeError(error_msg)
        return results
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)
            process.close()
        output.close()
        output.join_thread()

class TestRedisRateLimitIntegration(TestCase):
    """Opt in to real Lua, expiration and independent-process quota checks."""

    async def asyncSetUp(self) -> None:
        """Require a Redis URL and create an isolated namespace.

        Returns
        -------
        None
            Initialize the integration store and its owned client.

        Raises
        ------
        SkipTest
            If the Redis integration URL is not configured.
        """
        url = os.environ.get("ORIONIS_HTTP_REDIS_URL")
        if not url:
            self.skipTest("Set ORIONIS_HTTP_REDIS_URL to run Redis integration tests.")
        self.settings = HTTPRateLimit(
            rate_limit_redis_url=url,
            rate_limit_redis_prefix=f"orionis:test:http-rate:{uuid4().hex}",
            rate_limit_redis_timeout_seconds=10,
        )
        self.store = RedisRateLimitStore(self.settings)
        self.client = self.store._RedisRateLimitStore__client

    async def asyncTearDown(self) -> None:
        """Delete test quota keys and release the owned connection pool.

        Returns
        -------
        None
            Remove the isolated namespace and close the store.
        """
        keys = [key async for key in self.client.scan_iter(
            match=f"{self.settings.rate_limit_redis_prefix}:*",
        )]
        if keys:
            await self.client.delete(*keys)
        await self.store.close()

    async def testConcurrentClientsShareExactlyOneQuota(self) -> None:
        """Share one quota across separately owned Redis clients.

        Returns
        -------
        None
            Verify concurrent clients accept exactly the configured quota.
        """
        other = RedisRateLimitStore(self.settings)
        try:
            results = await asyncio.gather(*(
                (self.store if index % 2 else other).hit("client", 13, 60)
                for index in range(100)
            ))
            self.assertEqual(sum(results), 13)
            redis_key = (f"{self.settings.rate_limit_redis_prefix}:"
                         f"{sha256(b'client').hexdigest()}")
            self.assertEqual(await self.client.zcard(redis_key), 13)
            self.assertGreater(await self.client.pttl(redis_key), 0)
        finally:
            await other.close()

    async def testIndependentProcessesShareOneQuota(self) -> None:
        """Keep the shared limit at seventeen across spawned processes.

        Returns
        -------
        None
            Verify independent workers enforce one shared quota.
        """
        results = await asyncio.to_thread(
            _run_processes,
            self.settings.rate_limit_redis_url,
            self.settings.rate_limit_redis_prefix,
        )
        self.assertEqual(sum(results), 17)

    async def testWindowExpiresAndRecreatedStoreRetainsQuota(self) -> None:
        """Retain accepted history on recreation, then admit after expiration.

        Returns
        -------
        None
            Verify Redis preserves quota state until its window expires.
        """
        self.assertTrue(await self.store.hit("client", 1, 1))
        await self.store.close()
        self.store = RedisRateLimitStore(self.settings)
        self.client = self.store._RedisRateLimitStore__client
        self.assertFalse(await self.store.hit("client", 1, 1))
        await asyncio.sleep(1.05)
        self.assertTrue(await self.store.hit("client", 1, 1))

    async def testWrongKeyTypeRaisesWithoutOverwritingState(self) -> None:
        """Preserve incompatible stored data instead of resetting its quota.

        Returns
        -------
        None
            Verify a Redis type error leaves the existing key unchanged.
        """
        redis_key = (f"{self.settings.rate_limit_redis_prefix}:"
                     f"{sha256(b'client').hexdigest()}")
        await self.client.set(redis_key, "unexpected-data")
        with self.assertRaises(ResponseError):
            await self.store.hit("client", 1, 60)
        self.assertEqual(await self.client.get(redis_key), b"unexpected-data")
