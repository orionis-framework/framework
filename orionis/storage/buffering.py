# ruff: noqa: PLC0415, TC003
"""Provide storage operations.

Includes ``read_chunks``, ``iterate_chunks``, ``spool_stream``.
"""

from __future__ import annotations
import asyncio
import tempfile
from collections.abc import AsyncIterable, AsyncIterator, Callable, Iterator
from typing import BinaryIO
from orionis.support.concurrency import complete_on_cancel

READ_BUFFER_SIZE = 1024 * 1024
"""Read buffer size used by ``buffering``."""


async def _close_buffer(
    close: Callable[[], object],
    primary: BaseException | None,
) -> None:
    """
    Drain one owned resource close without replacing an active failure.

    Parameters
    ----------
    close : collections.abc.Callable
        Synchronous close callback for an owned handle or SDK iterator.
    primary : BaseException or None
        Error already propagating from the stream, including control signals.

    Returns
    -------
    None
        No return value.

    Raises
    ------
    Exception
        If cleanup fails without an earlier stream failure.
    asyncio.CancelledError
        If the caller is cancelled, after the close completes.
    """
    try:
        await complete_on_cancel(asyncio.to_thread(close))
    except Exception as error:
        if primary is None:
            raise
        from orionis.failure.runtime import capture_nowait

        if not isinstance(
            primary,
            (
                asyncio.CancelledError,
                KeyboardInterrupt,
                SystemExit,
                GeneratorExit,
            ),
        ):
            capture_nowait(primary, flow="storage", phase="stream")
        capture_nowait(error, flow="storage", phase="cleanup", operation="stream.close")


async def read_chunks(
    opener: Callable[[], BinaryIO],
    chunk_size: int,
    *,
    buffer_size: int = READ_BUFFER_SIZE,
) -> AsyncIterator[bytes]:
    """
    Read bounded batches while preserving logical chunks and first-byte latency.

    Parameters
    ----------
    opener : collections.abc.Callable[[], typing.BinaryIO]
        Factory for a handle owned exclusively by this iterator.
    chunk_size : int
        Maximum bytes yielded per logical chunk.
    buffer_size : int
        Read-ahead budget, rounded down to a whole number of logical chunks.
        At least one chunk is read. No producer runs while the consumer pauses.

    Yields
    ------
    bytes
        File content in order. Cancellation drains the current read before close.
        Cleanup failures are observed separately when a read already failed.
    """
    if (
        isinstance(chunk_size, bool)
        or not isinstance(chunk_size, int)
        or chunk_size < 1
        or isinstance(buffer_size, bool)
        or not isinstance(buffer_size, int)
        or buffer_size < 1
    ):
        error_msg = "Stream chunk and buffer sizes must be positive integers."
        raise ValueError(error_msg)
    handles = []

    def open_handle() -> None:
        """
        Retain ownership even if cancellation races with opening the file.

        Returns
        -------
        None
            No return value.
        """
        handles.append(opener())

    primary = None
    try:
        await complete_on_cancel(asyncio.to_thread(open_handle))
        handle = handles[0]
        read_size = chunk_size
        batch_size = max(chunk_size, buffer_size // chunk_size * chunk_size)
        while True:
            data = await complete_on_cancel(asyncio.to_thread(handle.read, read_size))
            if not data:
                return
            for offset in range(0, len(data), chunk_size):
                yield data[offset : offset + chunk_size]
            read_size = batch_size
    except BaseException as error:
        primary = error
        raise
    finally:
        if handles:
            await _close_buffer(handles[0].close, primary)


async def iterate_chunks(
    opener: Callable[[], Iterator[bytes]],
) -> AsyncIterator[bytes]:
    """
    Batch SDK iterator advances with bounded read-ahead and deterministic close.

    Parameters
    ----------
    opener : collections.abc.Callable[[], collections.abc.Iterator[bytes]]
        Synchronous factory for a request-owned SDK iterator.

    Yields
    ------
    bytes
        Original SDK chunks. A batch holds at most sixteen chunks and stops
        when it reaches 1 MiB, so memory is bounded by 1 MiB plus one SDK chunk.
        A cleanup failure does not replace the iterator's original failure.
    """
    iterators = []
    exhausted = object()

    def open_iterator() -> None:
        """
        Capture iterator ownership even when opening is cancelled.

        Returns
        -------
        None
            No return value.
        """
        iterators.append(iter(opener()))

    def read_batch(limit: int) -> list[bytes]:
        """
        Advance only until the item or byte budget is exhausted.

        Parameters
        ----------
        limit : int
            Maximum number of iterator items to read.

        Returns
        -------
        list[bytes]
            Chunks collected before reaching the item or byte budget.
        """
        result = []
        size = 0
        for _ in range(limit):
            chunk = next(iterators[0], exhausted)
            if chunk is exhausted:
                break
            result.append(chunk)
            size += len(chunk)
            if size >= READ_BUFFER_SIZE:
                break
        return result

    primary = None
    try:
        await complete_on_cancel(asyncio.to_thread(open_iterator))
        limit = 1
        while batch := await complete_on_cancel(asyncio.to_thread(read_batch, limit)):
            for chunk in batch:
                yield chunk
            limit = 16
    except BaseException as error:
        primary = error
        raise
    finally:
        if iterators and callable(close := getattr(iterators[0], "close", None)):
            await _close_buffer(close, primary)


async def spool_stream(stream: AsyncIterable[bytes], *, max_size: int) -> BinaryIO:
    """
    Buffer an async upload once for the cloud drivers.

    Parameters
    ----------
    stream : collections.abc.AsyncIterable[bytes]
        Asynchronous byte-chunk producer.
    max_size : int
        Positive maximum in-memory bytes before the buffer spills to disk.

    Returns
    -------
    typing.BinaryIO
        Rewound temporary buffer owned and closed by the uploading driver.

    Raises
    ------
    ValueError
        If max_size is not a positive integer or is a boolean.

    Notes
    -----
    Cancellation drains native opening, writing, and seeking before cleanup.
    Cleanup failures do not replace the producer or buffer failure.
    """
    if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 1:
        error_msg = "Spool memory limit must be a positive integer."
        raise ValueError(error_msg)
    opening = asyncio.create_task(
        asyncio.to_thread(tempfile.SpooledTemporaryFile, max_size=max_size),
    )
    try:
        buffer = await complete_on_cancel(opening)
        async for chunk in stream:
            await complete_on_cancel(asyncio.to_thread(buffer.write, chunk))
        await complete_on_cancel(asyncio.to_thread(buffer.seek, 0))
    except BaseException as error:
        if not opening.cancelled() and opening.exception() is None:
            await _close_buffer(opening.result().close, error)
        raise
    return buffer
