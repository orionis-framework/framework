# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import asyncio
import io
import threading
from typing import TYPE_CHECKING, Self, get_type_hints
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from orionis.failure.runtime import capture, operation
from orionis.storage.buffering import iterate_chunks, read_chunks, spool_stream
from orionis.storage.stream import AsyncStream
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Callable, Iterator


async def close_chunks(chunks: AsyncGenerator[bytes]) -> None:
    """Close a chunk generator through a coroutine recognized by unittest.

    Parameters
    ----------
    chunks : AsyncGenerator[bytes]
        Generator whose asynchronous cleanup must finish before teardown.

    Returns
    -------
    None
        No return value.
    """
    await chunks.aclose()


class TestBufferedStreams(TestCase):
    """Validate read budgets, backpressure and resource ownership under cancellation."""

    def testPublicBufferAnnotationsResolveAtRuntime(self) -> None:
        """Resolve the public buffered streaming signatures at runtime."""
        for function in (read_chunks, iterate_chunks, spool_stream):
            with self.subTest(function=function.__name__):
                self.assertIn("return", get_type_hints(function))

    async def testBoundedReadsAndEarlyClose(self: Self) -> None:
        """
        Preserve first-byte reads and batch without prefetching while paused.

        Returns
        -------
        None
            No return value.
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
        self.addCleanup(handle.close)
        chunks = read_chunks(lambda: handle, 10, buffer_size=100)
        self.addAsyncCleanup(close_chunks, chunks)
        self.assertEqual(await anext(chunks), b"abcdefabcd")
        self.assertEqual(sizes, [10])
        marker = asyncio.Event()
        asyncio.get_running_loop().call_soon(marker.set)
        await marker.wait()
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
            No return value.
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
                if not released.wait(5):
                    error_msg = "The test did not release the native read."
                    raise TimeoutError(error_msg)
                events.append("read")
                return super().read(size)

            def close(self: Self) -> None:
                """
                Record the close event and release the in-memory buffer.

                Returns
                -------
                None
                    No return value.
                """
                events.append("close")
                super().close()

        handle = Handle(b"bytes")
        self.addCleanup(handle.close)
        chunks = read_chunks(lambda: handle, 2)
        self.addAsyncCleanup(close_chunks, chunks)
        reading = asyncio.create_task(anext(chunks))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 5))
            reading.cancel()
            marker = asyncio.Event()
            asyncio.get_running_loop().call_soon(marker.set)
            await marker.wait()
            self.assertEqual(events, [])
        finally:
            released.set()
            if not reading.done() and not reading.cancelling():
                reading.cancel()
            outcome = await asyncio.gather(reading, return_exceptions=True)
        self.assertIsInstance(outcome[0], asyncio.CancelledError)
        self.assertEqual(events, ["read", "close"])

    async def testAsyncStreamBytesAndSdkIteratorClose(self: Self) -> None:
        """
        Preserve complete content with bounded batches and explicit ownership.

        Returns
        -------
        None
            No return value.
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
            No return value.
        """
        for iterator in (False, True):
            with self.subTest(iterator=iterator):
                app, runtime, handler = activate_runtime()
                self.addAsyncCleanup(runtime.shutdown)
                primary, secondary = OSError("read"), OSError("close")
                handle = MagicMock()
                handle.read.side_effect = primary
                handle.__iter__.side_effect = lambda item=handle: item
                handle.__next__.side_effect = primary
                handle.close.side_effect = secondary
                opener = MagicMock(return_value=handle)
                chunks = iterate_chunks(opener) if iterator else read_chunks(opener, 2)
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
                cleanup_context = next(
                    ctx for error, ctx in handler.failures if error is secondary
                )
                primary_context = next(
                    ctx for error, ctx in handler.failures if error is primary
                )
                self.assertEqual(cleanup_context.flow, "storage")
                self.assertEqual(cleanup_context.phase, "cleanup")
                self.assertEqual(
                    cleanup_context.parent_event_id,
                    primary_context.event_id,
                )
                self.assertIs(secondary.__context__, primary)
                handle.close.assert_called_once()

    async def testSpoolCancellationDrainsWriteBeforeClosing(self) -> None:
        """Retain ownership of a spool until its native write has completed.

        Returns
        -------
        None
            No return value.
        """
        entered, closing = asyncio.Event(), asyncio.Event()
        release = threading.Event()
        events = []
        loop = asyncio.get_running_loop()

        def write(_chunk: bytes) -> None:
            """Block the native write until the test releases its worker."""
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                error_msg = "The test did not release the spool writer."
                raise TimeoutError(error_msg)
            events.append("write")

        def close() -> None:
            """Record spool disposal and notify the owning event loop."""
            events.append("close")
            loop.call_soon_threadsafe(closing.set)

        async def source() -> AsyncIterator[bytes]:
            """Yield one upload chunk for the blocked write."""
            yield b"payload"

        buffer = SimpleNamespace(write=write, close=close, seek=MagicMock())
        to_thread = asyncio.to_thread

        async def run_thread(
            callback: Callable[..., object],
            *args: object,
            **kwargs: object,
        ) -> object:
            """Expose premature close synchronously and offload other callbacks."""
            if callback is close:
                return callback()
            return await to_thread(callback, *args, **kwargs)

        with (
            patch(
                "orionis.storage.buffering.tempfile.SpooledTemporaryFile",
                return_value=buffer,
            ),
            patch("orionis.storage.buffering.asyncio.to_thread", run_thread),
        ):
            task = asyncio.create_task(spool_stream(source(), max_size=100))
            try:
                await asyncio.wait_for(entered.wait(), 2)
                task.cancel()
                # Give cancellation a deterministic opportunity to reach cleanup.
                marker = asyncio.Event()
                loop.call_soon(marker.set)
                await marker.wait()
                was_closing = closing.is_set()
            finally:
                release.set()
                if not task.done() and not task.cancelling():
                    task.cancel()
                outcome = await asyncio.gather(task, return_exceptions=True)
        self.assertIsInstance(outcome[0], asyncio.CancelledError)
        self.assertFalse(was_closing)
        self.assertEqual(events, ["write", "close"])

    async def testSpoolFailureSurvivesCloseFailure(self) -> None:
        """Preserve the upload producer error while observing spool cleanup.

        Returns
        -------
        None
            No return value.
        """
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        primary, secondary = OSError("producer"), OSError("spool close")
        buffer = MagicMock()
        buffer.close.side_effect = secondary

        async def source() -> AsyncIterator[bytes]:
            """Yield a chunk and then propagate the original producer error."""
            yield b"payload"
            raise primary

        with (
            operation(app),
            patch(
                "orionis.storage.buffering.tempfile.SpooledTemporaryFile",
                return_value=buffer,
            ),
        ):
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
            No return value.
        """
        for persist in (False, True):
            with self.subTest(persist=persist):
                app, runtime, handler = activate_runtime()
                self.addAsyncCleanup(runtime.shutdown)
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
                self.assertEqual(
                    handler.failures[1][1].parent_event_id,
                    handler.failures[0][1].event_id,
                )
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
            No return value.
        """
        for spool in (False, True):
            with self.subTest(spool=spool):
                app, runtime, handler = activate_runtime()
                self.addAsyncCleanup(runtime.shutdown)
                entered, release = asyncio.Event(), threading.Event()
                loop = asyncio.get_running_loop()
                failure = OSError("late close")
                handle = MagicMock()
                handle.close.side_effect = failure

                def open_handle(
                    owner_loop: asyncio.AbstractEventLoop = loop,
                    started: asyncio.Event = entered,
                    gate: threading.Event = release,
                    result: MagicMock = handle,
                    **_kwargs: object,
                ) -> MagicMock:
                    """Return the late handle after the test releases the worker."""
                    owner_loop.call_soon_threadsafe(started.set)
                    if not gate.wait(5):
                        error_msg = "The test did not release the handle opener."
                        raise TimeoutError(error_msg)
                    return result

                async def source() -> AsyncIterator[bytes]:
                    """Yield a payload for the spool opened by the worker."""
                    yield b"payload"

                with (
                    operation(app),
                    patch(
                        "orionis.storage.buffering.tempfile.SpooledTemporaryFile",
                        side_effect=open_handle,
                    ),
                ):
                    pending = (
                        spool_stream(source(), max_size=100)
                        if spool
                        else AsyncStream(open_handle).__aenter__()
                    )
                    task = asyncio.create_task(pending)
                    try:
                        await asyncio.wait_for(entered.wait(), 2)
                        task.cancel()
                    finally:
                        release.set()
                        if not task.done() and not task.cancelling():
                            task.cancel()
                        outcome = await asyncio.gather(task, return_exceptions=True)
                    self.assertIsInstance(outcome[0], asyncio.CancelledError)
                    await runtime.drain()
                handle.close.assert_called_once()
                self.assertEqual(handler.reports, [failure])
                self.assertEqual(handler.failures[0][1].phase, "cleanup")
