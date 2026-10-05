import asyncio
from orionis.mcp.streams import OwnedStream
from orionis.test import TestCase

class _Source:
    """A stateful source that owns cleanup before iteration starts."""

    def __init__(self) -> None:
        """Initialize the test double.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.reads = 0
        self.closes = 0
        self.closing = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()

    def __aiter__(self) -> _Source:
        """Return the asynchronous iterator.

        Returns
        -------
        _Source
            Return the result produced by ``__aiter__``.
        """
        return self

    async def __anext__(self) -> int:
        """Return the next asynchronous item.

        Returns
        -------
        int
            Return the result produced by ``__anext__``.
        """
        self.reads += 1
        return self.reads

    async def aclose(self):
        """Close the asynchronous iterator.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.closing.set()
        await self.release.wait()
        self.closes += 1

class TestOwnedStreams(TestCase):
    """Keep cleanup reliable when delivery never starts or is cancelled twice."""

    async def test_unstarted_outer_closes_source_once(self):
        """Close both owners before the outer generator enters its body.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        source = _Source()
        owner = OwnedStream(source)

        async def frames():
            """Yield protocol frames for the test request.

            Yields
            ------
            object
                Values produced by the asynchronous or synchronous fixture.
            """
            async for item in owner:
                yield item

        stream = OwnedStream(frames(), owner)
        await stream.aclose()
        await owner.aclose()
        self.assertEqual((source.reads, source.closes), (0, 1))

    async def test_backpressure_has_no_prefetch(self):
        """Advance the source only after the consumer asks for an item.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        source = _Source()
        stream = OwnedStream(source)
        self.assertEqual(source.reads, 0)
        self.assertEqual(await anext(stream), 1)
        await asyncio.sleep(0)
        self.assertEqual(source.reads, 1)
        await stream.aclose()

    async def test_repeated_cancellation_joins_cleanup(self):
        """Preserve finalization when the owner is cancelled more than once.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        source = _Source()
        source.release.clear()
        stream = OwnedStream(source)
        close = asyncio.create_task(stream.aclose())
        await source.closing.wait()
        close.cancel()
        await asyncio.sleep(0)
        close.cancel()
        await asyncio.sleep(0)
        self.assertFalse(close.done())
        source.release.set()
        with self.assertRaises(asyncio.CancelledError):
            await close
        self.assertEqual(source.closes, 1)

    async def test_synchronous_generator_finally(self):
        """Run synchronous generator cleanup after early stream closure.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        closed = []

        def values():
            """Yield values from the synchronous test source.

            Yields
            ------
            object
                Values produced by the asynchronous or synchronous fixture.
            """
            try:
                yield 1
                yield 2
            finally:
                closed.append(True)

        stream = OwnedStream(values())
        self.assertEqual(await anext(stream), 1)
        await stream.aclose()
        self.assertEqual(closed, [True])
