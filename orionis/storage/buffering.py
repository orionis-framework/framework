from __future__ import annotations
import asyncio
import tempfile
from typing import TYPE_CHECKING
from orionis.support.concurrency import complete_on_cancel

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator, Callable, Iterator
    from typing import BinaryIO

READ_BUFFER_SIZE = 1024 * 1024

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
    opener : Callable[[], BinaryIO]
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
            Complete the operation without returning a value.
        """
        handles.append(opener())

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
    finally:
        if handles:
            await complete_on_cancel(asyncio.to_thread(handles[0].close))

async def iterate_chunks(
    opener: Callable[[], Iterator[bytes]],
) -> AsyncIterator[bytes]:
    """
    Batch SDK iterator advances with bounded read-ahead and deterministic close.

    Parameters
    ----------
    opener : Callable[[], Iterator[bytes]]
        Synchronous factory for a request-owned SDK iterator.

    Yields
    ------
    bytes
        Original SDK chunks. A batch holds at most sixteen chunks and stops
        when it reaches 1 MiB, so memory is bounded by 1 MiB plus one SDK chunk.
    """
    iterators = []

    def open_iterator() -> None:
        """
        Capture iterator ownership even when opening is cancelled.

        Returns
        -------
        None
            Complete the operation without returning a value.
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
            chunk = next(iterators[0], b"")
            if not chunk:
                break
            result.append(chunk)
            size += len(chunk)
            if size >= READ_BUFFER_SIZE:
                break
        return result

    try:
        await complete_on_cancel(asyncio.to_thread(open_iterator))
        limit = 1
        while batch := await complete_on_cancel(asyncio.to_thread(read_batch, limit)):
            for chunk in batch:
                yield chunk
            limit = 16
    finally:
        if iterators and callable(close := getattr(iterators[0], "close", None)):
            await complete_on_cancel(asyncio.to_thread(close))

async def spool_stream(stream: AsyncIterable[bytes], *, max_size: int) -> BinaryIO:
    """
    Buffer an async upload once for the cloud drivers.

    Parameters
    ----------
    stream : AsyncIterable[bytes]
        Asynchronous byte-chunk producer.
    max_size : int
        Maximum in-memory bytes before the buffer spills to disk.

    Returns
    -------
    BinaryIO
        Rewound temporary buffer owned and closed by the uploading driver.
    """
    buffer = await asyncio.to_thread(tempfile.SpooledTemporaryFile, max_size=max_size)
    try:
        async for chunk in stream:
            await asyncio.to_thread(buffer.write, chunk)
        await asyncio.to_thread(buffer.seek, 0)
    except BaseException:
        await asyncio.to_thread(buffer.close)
        raise
    return buffer
