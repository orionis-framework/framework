import asyncio
import io
import threading
from typing import TYPE_CHECKING, Self
from orionis.storage.buffering import iterate_chunks, read_chunks
from orionis.storage.stream import AsyncStream
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator

class TestBufferedStreams(TestCase):
    """Validate read budgets, backpressure and resource ownership under cancellation."""

    async def testBoundedReadsAndEarlyClose(self: Self) -> None:
        """
        Preserve first-byte reads and batch without prefetching while paused.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        sizes = []

        class Handle(io.BytesIO):
            def read(self: Self, size: int = -1) -> bytes:
                """
                Observe the native read before returning bytes from the buffer.

                Parameters
                ----------
                size : int
                    Maximum number of bytes to read; negative values read all bytes.

                Returns
                -------
                bytes
                    Bytes read from the underlying in-memory buffer.
                """
                sizes.append(size)
                return super().read(size)

        handle = Handle(b"abcdef" * 100)
        chunks = read_chunks(lambda: handle, 10, buffer_size=100)
        self.assertEqual(await anext(chunks), b"abcdefabcd")
        self.assertEqual(sizes, [10])
        await asyncio.sleep(0.01)
        self.assertEqual(sizes, [10])
        await anext(chunks)
        self.assertEqual(sizes, [10, 100])
        await chunks.aclose()
        self.assertTrue(handle.closed)

    async def testCancellationWaitsForReadBeforeClose(self: Self) -> None:
        """
        Do not close an SDK/file handle while its native read is running.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        entered, released = threading.Event(), threading.Event()
        events = []

        class Handle(io.BytesIO):
            def read(self: Self, size: int = -1) -> bytes:
                """
                Observe the native read before returning bytes from the buffer.

                Parameters
                ----------
                size : int
                    Maximum number of bytes to read; negative values read all bytes.

                Returns
                -------
                bytes
                    Bytes read from the underlying in-memory buffer.
                """
                entered.set()
                released.wait(5)
                events.append("read")
                return super().read(size)

            def close(self: Self) -> None:
                """
                Record the close event and release the in-memory buffer.

                Returns
                -------
                None
                    Complete the operation without returning a value.
                """
                events.append("close")
                super().close()

        handle = Handle(b"bytes")
        chunks = read_chunks(lambda: handle, 2)
        reading = asyncio.create_task(anext(chunks))
        try:
            await asyncio.to_thread(entered.wait, 5)
            reading.cancel()
            await asyncio.sleep(0.01)
            self.assertEqual(events, [])
        finally:
            released.set()
            with self.assertRaises(asyncio.CancelledError):
                await reading
        self.assertEqual(events, ["read", "close"])

    async def testAsyncStreamBytesAndSdkIteratorClose(self: Self) -> None:
        """
        Preserve complete content with bounded batches and explicit ownership.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        handle = io.BytesIO(bytes(range(256)) * 100)
        async with AsyncStream(lambda: handle) as stream:
            chunks = [chunk async for chunk in stream.chunks(64, buffer_size=1024)]
        self.assertEqual(b"".join(chunks), bytes(range(256)) * 100)
        self.assertTrue(handle.closed)
        closed = []

        def source() -> Iterator[bytes]:
            """
            Yield SDK-style byte chunks and record iterator cleanup.

            Yields
            ------
            bytes
                Successive byte chunks from the simulated SDK iterator.
            """
            try:
                yield from [b"a", b"b", b"c"]
            finally:
                closed.append(True)

        chunks = iterate_chunks(source)
        self.assertEqual(await anext(chunks), b"a")
        await chunks.aclose()
        self.assertEqual(closed, [True])
