from redis.exceptions import ConnectionError as RedisConnectionError
from orionis.foundation.config.http import HTTP
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.http.kernel import KernelHTTP
from orionis.http.layer.shared.rate_limit import RateLimitMiddleware
from orionis.http.layer.store.redis_rate_limit import RedisRateLimitStore
from orionis.http.responses import Response
from orionis.test import TestCase
from tests.http.test_support import make_adapter

class _DefaultResponses:
    """Render error status and headers for middleware assertions."""

    __slots__ = ()

    @staticmethod
    async def error(
        *, status_code: int, content: str, headers: dict, **_kwargs: object,
    ) -> Response:
        """Build an error response for middleware assertions.

        Parameters
        ----------
        status_code : int
            HTTP status code to return.
        content : str
            Error response body.
        headers : dict
            Headers to include in the response.
        **_kwargs : object
            Additional response options, ignored by this test double.

        Returns
        -------
        Response
            The requested error response.
        """
        return Response(status_code=status_code, content=content, headers=headers)

class _UnavailableStore:
    """Fail instead of silently admitting requests when storage is unavailable."""

    __slots__ = ()

    @staticmethod
    async def hit(_key: str, _limit: int, _window: int) -> bool:
        """Simulate a failed request to the distributed quota backend.

        Parameters
        ----------
        _key : str
            Quota key supplied by the middleware.
        _limit : int
            Request limit supplied by the middleware.
        _window : int
            Quota window in seconds.

        Raises
        ------
        RedisConnectionError
            Always, to simulate an unavailable backend.
        """
        raise RedisConnectionError

class _Application:
    """Record the HTTP kernel's application shutdown callback."""

    __slots__ = ("callbacks",)

    def __init__(self) -> None:
        """Initialize an empty shutdown-hook recorder.

        Returns
        -------
        None
            Prepare the callback collection.
        """
        self.callbacks = []

    def on(self, event: Lifespan, callback: object, *, runtime: Runtime) -> None:
        """Record a callback with its lifecycle event and runtime.

        Parameters
        ----------
        event : Lifespan
            Application lifecycle event associated with the callback.
        callback : object
            Callback registered by the kernel.
        runtime : Runtime
            Runtime associated with the callback.

        Returns
        -------
        None
            Append the lifecycle callback to the recorder.
        """
        self.callbacks.append((event, callback, runtime))

class _ClosingClient:
    """Report when an owned Redis pool is closed by application shutdown."""

    __slots__ = ("closed",)

    def __init__(self) -> None:
        """Initialize the connection-pool marker as open.

        Returns
        -------
        None
            Prepare the closure marker for shutdown assertions.
        """
        self.closed = False

    async def aclose(self) -> None:
        """Record pool closure without opening a Redis connection.

        Returns
        -------
        None
            Mark the owned connection pool as closed.
        """
        self.closed = True

class TestRateLimitMiddleware(TestCase):
    """Verify configured capacity and distributed failure behavior."""

    async def testMemoryCapacityRejectsWithRetryAfter(self) -> None:
        """Reject a new client when the in-memory key capacity is full.

        Returns
        -------
        None
            Verify capacity rejection includes the retry interval.
        """
        middleware = RateLimitMiddleware({
            "rate_limit_enabled": True,
            "rate_limit_max_keys": 1,
            "rate_limit_requests": 2,
        }, _DefaultResponses())
        first = make_adapter([])
        first.setClient("192.0.2.1")
        second = make_adapter([])
        second.setClient("192.0.2.2")
        self.assertIsNone(await middleware.handle(first))
        rejected = await middleware.handle(second)
        self.assertEqual(rejected.getStatusCode(), 429)
        self.assertEqual(rejected.getHeader("Retry-After"), ["60"])
        self.assertIsNone(await middleware.handle(first))
        self.assertEqual((await middleware.handle(first)).getStatusCode(), 429)

    async def testRedisFailureReturnsServiceUnavailable(self) -> None:
        """Return 503 when Redis is unavailable instead of using a local quota.

        Returns
        -------
        None
            Verify backend failure does not silently switch quota stores.
        """
        middleware = RateLimitMiddleware({"rate_limit_enabled": True},
                                         _DefaultResponses())
        middleware._RateLimitMiddleware__store = _UnavailableStore()
        adapter = make_adapter([])
        adapter.setClient("192.0.2.1")
        result = await middleware.handle(adapter)
        self.assertEqual(result.getStatusCode(), 503)
        self.assertEqual(result.getHeader("Retry-After"), ["1"])

    async def testRedisBackendIsLazyAndDisabledLimiterNeedsNoStore(self) -> None:
        """Create the Redis store only for an enabled limiter.

        Returns
        -------
        None
            Verify store construction is lazy and disabled limits need no store.
        """
        middleware = RateLimitMiddleware({
            "rate_limit_enabled": True, "rate_limit_store": "redis",
        }, _DefaultResponses())
        self.assertIsInstance(middleware._RateLimitMiddleware__store,
                              RedisRateLimitStore)
        await middleware.close()
        disabled = RateLimitMiddleware({"rate_limit_store": "redis"},
                                       _DefaultResponses())
        self.assertIsNone(disabled._RateLimitMiddleware__store)
        self.assertIsNone(await disabled.handle(make_adapter([])))
        await disabled.close()

    async def testKernelRegistersRedisPoolClosureForHTTPShutdown(self) -> None:
        """Close the owned Redis store through the kernel shutdown hook.

        Returns
        -------
        None
            Verify HTTP shutdown closes the middleware's owned pool.
        """
        app = _Application()
        kernel = KernelHTTP(app, None)
        config = HTTP(rate_limit={
            "rate_limit_enabled": True, "rate_limit_store": "redis",
        }).toDict()
        kernel._KernelHTTP__defaultMiddleware(config, _DefaultResponses())
        self.assertEqual(len(app.callbacks), 1)
        event, callback, runtime = app.callbacks[0]
        self.assertEqual(event, Lifespan.SHUTDOWN)
        self.assertEqual(runtime, Runtime.HTTP)
        transport = _ClosingClient()
        middleware = kernel._KernelHTTP__rate_limit
        middleware._RateLimitMiddleware__store._RedisRateLimitStore__client = transport
        await callback()
        self.assertTrue(transport.closed)
