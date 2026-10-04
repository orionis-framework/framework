"""Exercise ownership and cancellation without transport-specific buffering."""

import asyncio
import unittest

from orionis.mcp.streams import OwnedStream


class _Source:
    """A stateful source that owns cleanup before iteration starts."""

    def __init__(self) -> None:
        self.reads = 0
        self.closes = 0
        self.closing = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()

    def __aiter__(self) -> _Source:
        return self

    async def __anext__(self) -> int:
        self.reads += 1
        return self.reads

    async def aclose(self):
        self.closing.set()
        await self.release.wait()
        self.closes += 1


class TestOwnedStreams(unittest.IsolatedAsyncioTestCase):
    """Keep cleanup reliable when delivery never starts or is cancelled twice."""

    async def test_unstarted_outer_closes_source_once(self):
        """Close both owners before the outer generator enters its body."""
        source = _Source()
        owner = OwnedStream(source)

        async def frames():
            async for item in owner:
                yield item

        stream = OwnedStream(frames(), owner)
        await stream.aclose()
        await owner.aclose()
        self.assertEqual((source.reads, source.closes), (0, 1))

    async def test_backpressure_has_no_prefetch(self):
        """Advance the source only after the consumer asks for an item."""
        source = _Source()
        stream = OwnedStream(source)
        self.assertEqual(source.reads, 0)
        self.assertEqual(await anext(stream), 1)
        await asyncio.sleep(0)
        self.assertEqual(source.reads, 1)
        await stream.aclose()

    async def test_repeated_cancellation_joins_cleanup(self):
        """Preserve finalization when the owner is cancelled more than once."""
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
        """Run synchronous generator cleanup after early stream closure."""
        closed = []

        def values():
            try:
                yield 1
                yield 2
            finally:
                closed.append(True)

        stream = OwnedStream(values())
        self.assertEqual(await anext(stream), 1)
        await stream.aclose()
        self.assertEqual(closed, [True])
