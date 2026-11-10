import asyncio
import io
import threading
from typing import TYPE_CHECKING, Self
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from orionis.failure.runtime import capture, operation
from orionis.storage.buffering import iterate_chunks, read_chunks, spool_stream
from orionis.storage.stream import AsyncStream
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime

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

    async def testReadAndIteratorCleanupPreserveOriginalFailure(self) -> None:
        """Observe failed cleanup without replacing a read or SDK iterator error.

        Returns
        -------
        None
            Keep the primary identity, original traceback, and one cleanup report.
        """
        for iterator in (False, True):
            with self.subTest(iterator=iterator):
                app, runtime, handler = activate_runtime()
                primary, secondary = OSError("read"), OSError("close")
                handle = MagicMock()
                handle.read.side_effect = primary
                handle.__iter__.side_effect = lambda item=handle: item
                handle.__next__.side_effect = primary
                handle.close.side_effect = secondary
                opener = MagicMock(return_value=handle)
                chunks = (iterate_chunks(opener) if iterator
                          else read_chunks(opener, 2))
                with operation(app):
                    try:
                        await anext(chunks)
                    except OSError as observed:
                        self.assertIs(observed, primary)
                        traceback = observed.__traceback__
                        await capture(observed, app=app, flow="http")
                        await runtime.drain()
                        self.assertIs(observed.__traceback__, traceback)
                        self.assertIsNotNone(traceback)
                    else:
                        self.fail("The storage read unexpectedly succeeded.")
                self.assertCountEqual(handler.reports, [primary, secondary])
                self.assertEqual(len(handler.failures), 2)
                cleanup_context = next(ctx for error, ctx in handler.failures
                                       if error is secondary)
                primary_context = next(ctx for error, ctx in handler.failures
                                       if error is primary)
                self.assertEqual(cleanup_context.flow, "storage")
                self.assertEqual(cleanup_context.phase, "cleanup")
                self.assertEqual(cleanup_context.parent_event_id,
                                 primary_context.event_id)
                self.assertIs(secondary.__context__, primary)
                handle.close.assert_called_once()

    async def testSpoolCancellationDrainsWriteBeforeClosing(self) -> None:
        """Retain ownership of a spool until its native write has completed.

        Returns
        -------
        None
            Close after writing finishes, without losing caller cancellation.
        """
        entered, closing = asyncio.Event(), asyncio.Event()
        release = threading.Event()
        events = []
        loop = asyncio.get_running_loop()

        def write(_chunk):
            loop.call_soon_threadsafe(entered.set)
            release.wait(5)
            events.append("write")

        def close():
            events.append("close")
            loop.call_soon_threadsafe(closing.set)

        async def source():
            yield b"payload"

        buffer = SimpleNamespace(write=write, close=close, seek=MagicMock())
        to_thread = asyncio.to_thread

        async def run_thread(callback, *args: object, **kwargs: object):
            if callback is close:
                return callback()
            return await to_thread(callback, *args, **kwargs)

        with (
            patch("orionis.storage.buffering.tempfile.SpooledTemporaryFile",
                  return_value=buffer),
            patch("orionis.storage.buffering.asyncio.to_thread", run_thread),
        ):
            task = asyncio.create_task(spool_stream(source(), max_size=100))
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            # Give cancellation a deterministic opportunity to reach cleanup.
            marker = asyncio.Event()
            loop.call_soon(marker.set)
            await marker.wait()
            was_closing = closing.is_set()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertFalse(was_closing)
        self.assertEqual(events, ["write", "close"])

    async def testSpoolFailureSurvivesCloseFailure(self) -> None:
        """Preserve the upload producer error while observing spool cleanup.

        Returns
        -------
        None
            Propagate the exact producer error and record cleanup once.
        """
        app, runtime, handler = activate_runtime()
        primary, secondary = OSError("producer"), OSError("spool close")
        buffer = MagicMock()
        buffer.close.side_effect = secondary

        async def source():
            yield b"payload"
            raise primary

        with (operation(app),
              patch("orionis.storage.buffering.tempfile.SpooledTemporaryFile",
                    return_value=buffer)):
            with self.assertRaises(OSError) as caught:
                await spool_stream(source(), max_size=100)
            await runtime.drain()
        self.assertIs(caught.exception, primary)
        self.assertEqual(handler.reports, [primary, secondary])
        buffer.close.assert_called_once()

    async def testStreamPreservesBodyAndPersistenceFailuresDuringClose(self) -> None:
        """Keep the owner failure when stream disposal fails too.

        Returns
        -------
        None
            Observe cleanup once and retain the body or persistence callback error.
        """
        for persist in (False, True):
            with self.subTest(persist=persist):
                app, runtime, handler = activate_runtime()
                primary, secondary = OSError("primary"), OSError("close")
                handle = MagicMock()
                handle.close.side_effect = secondary
                callback = MagicMock(side_effect=primary) if persist else None
                stream = AsyncStream(MagicMock(return_value=handle), callback)
                with operation(app), self.assertRaises(OSError) as caught:
                    async with stream:
                        if not persist:
                            raise primary
                await runtime.drain()
                self.assertIs(caught.exception, primary)
                self.assertEqual(handler.reports, [primary, secondary])
                self.assertEqual(handler.failures[1][1].phase, "cleanup")
                self.assertEqual(handler.failures[1][1].parent_event_id,
                                 handler.failures[0][1].event_id)
                handle.close.assert_called_once()
                if callback is not None:
                    callback.assert_called_once_with(handle)

    async def testCancelledOpeningClosesLateResourcesWithoutReplacingCancellation(
        self,
    ) -> None:
        """Close late spool and stream handles even if their cleanup also fails.

        Returns
        -------
        None
            Preserve cancellation and observe the cleanup exception once.
        """
        for spool in (False, True):
            with self.subTest(spool=spool):
                app, runtime, handler = activate_runtime()
                entered, release = asyncio.Event(), threading.Event()
                loop = asyncio.get_running_loop()
                failure = OSError("late close")
                handle = MagicMock()
                handle.close.side_effect = failure

                def open_handle(
                    owner_loop=loop, started=entered, gate=release, result=handle,
                    **_kwargs: object,
                ):
                    owner_loop.call_soon_threadsafe(started.set)
                    gate.wait(5)
                    return result

                async def source():
                    yield b"payload"

                with (
                    operation(app),
                    patch("orionis.storage.buffering.tempfile.SpooledTemporaryFile",
                          side_effect=open_handle),
                ):
                    pending = (spool_stream(source(), max_size=100) if spool
                               else AsyncStream(open_handle).__aenter__())
                    task = asyncio.create_task(pending)
                    await asyncio.wait_for(entered.wait(), 2)
                    task.cancel()
                    release.set()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                    await runtime.drain()
                handle.close.assert_called_once()
                self.assertEqual(handler.reports, [failure])
                self.assertEqual(handler.failures[0][1].phase, "cleanup")
