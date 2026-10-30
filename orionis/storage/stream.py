from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Self
from orionis.storage.buffering import READ_BUFFER_SIZE
from orionis.storage.contracts.stream import IStorageStream
from orionis.support.concurrency import complete_on_cancel

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from types import TracebackType
    from typing import BinaryIO

class AsyncStream(IStorageStream):
    """
    Asynchronous wrapper around a lazily opened binary handle.

    The underlying handle is produced by *opener* on first use (or on
    ``__aenter__``) and every blocking operation is executed on a
    worker thread, keeping the event loop responsive. Drivers may
    provide an *on_close* callback to persist buffered data before the
    handle is released.
    """

    __slots__ = ("_handle", "_lock", "_on_close", "_opener")

    def __init__(
        self: Self,
        opener: Callable[[], BinaryIO],
        on_close: Callable[[BinaryIO], None] | None = None,
    ) -> None:
        """
        Initialize the stream with its handle factory.

        Parameters
        ----------
        opener : Callable[[], BinaryIO]
            Zero-argument callable returning the binary handle. It is
            invoked lazily on a worker thread.
        on_close : Callable[[BinaryIO], None] | None
            Optional callback executed with the open handle right
            before it is closed.

        Returns
        -------
        None
        """
        self._opener = opener
        self._on_close = on_close
        self._handle: BinaryIO | None = None
        self._lock = asyncio.Lock()

    async def __ensureHandle(self: Self) -> BinaryIO:
        """
        Open the underlying handle on first use and return it.

        Returns
        -------
        BinaryIO
            The open binary handle backing this stream.
        """
        # Open lazily so building the stream object stays side-effect free.
        if self._handle is None:

            def open_handle() -> None:
                """
                Retain the handle if cancellation races with creation.

                Returns
                -------
                None
                    Complete the operation without returning a value.
                """
                self._handle = self._opener()

            try:
                await complete_on_cancel(asyncio.to_thread(open_handle))
            except asyncio.CancelledError:
                handle, self._handle = self._handle, None
                if handle is not None:
                    await complete_on_cancel(asyncio.to_thread(handle.close))
                raise
        return self._handle

    async def read(self: Self, size: int = -1) -> bytes:
        """
        Read up to *size* bytes from the stream.

        Parameters
        ----------
        size : int
            Maximum number of bytes to read. ``-1`` reads until EOF.

        Returns
        -------
        bytes
            Bytes read from the current position; empty at EOF.
        """
        async with self._lock:
            handle = await self.__ensureHandle()
            return await complete_on_cancel(asyncio.to_thread(handle.read, size))

    async def chunks(
        self: Self,
        size: int = 65536,
        *,
        buffer_size: int = READ_BUFFER_SIZE,
    ) -> AsyncIterator[bytes]:
        """
        Yield logical chunks with bounded batching of synchronous reads.

        Parameters
        ----------
        size : int
            Maximum yielded bytes per chunk.
        buffer_size : int
            Read-ahead budget, at least one logical chunk.

        Yields
        ------
        bytes
            Sequential content. The surrounding async context owns close;
            callers must not mix iteration with writes, seek or other reads.
        """
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 1
            or isinstance(buffer_size, bool)
            or not isinstance(buffer_size, int)
            or buffer_size < 1
        ):
            error_msg = "Stream chunk and buffer sizes must be positive integers."
            raise ValueError(error_msg)
        read_size = size
        while data := await self.read(read_size):
            for offset in range(0, len(data), size):
                yield data[offset : offset + size]
            read_size = max(size, buffer_size // size * size)

    async def write(self: Self, data: bytes) -> int:
        """
        Write *data* to the stream at the current position.

        Parameters
        ----------
        data : bytes
            Raw bytes to write.

        Returns
        -------
        int
            Number of bytes written.
        """
        async with self._lock:
            handle = await self.__ensureHandle()
            return await complete_on_cancel(asyncio.to_thread(handle.write, data))

    async def seek(self: Self, offset: int, whence: int = 0) -> int:
        """
        Move the stream position to *offset*.

        Parameters
        ----------
        offset : int
            Target offset relative to *whence*.
        whence : int
            Anchor point: ``0`` start, ``1`` current, ``2`` end.

        Returns
        -------
        int
            The new absolute position within the stream.
        """
        async with self._lock:
            handle = await self.__ensureHandle()
            return await complete_on_cancel(
                asyncio.to_thread(handle.seek, offset, whence),
            )

    async def close(self: Self) -> None:
        """
        Flush pending data and release the underlying handle.

        Invokes the *on_close* callback (when provided) before closing
        the handle. Closing an unopened or already closed stream is a
        no-op.

        Returns
        -------
        None
        """
        async with self._lock:
            handle = self._handle
            if handle is None:
                return
            self._handle = None

            def close_handle() -> None:
                """
                Release the file even when the persistence callback fails.

                Returns
                -------
                None
                    Complete the operation without returning a value.
                """
                try:
                    if self._on_close is not None:
                        self._on_close(handle)
                finally:
                    handle.close()

            await complete_on_cancel(asyncio.to_thread(close_handle))

    async def __aenter__(self: Self) -> IStorageStream:
        """
        Open the underlying handle and return the stream.

        Returns
        -------
        IStorageStream
            The stream itself, ready for I/O operations.
        """
        async with self._lock:
            await self.__ensureHandle()
        return self

    async def __aexit__(
        self: Self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Close the stream when leaving the async context.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception class raised inside the context, if any.
        exc : BaseException | None
            Exception instance raised inside the context, if any.
        traceback : TracebackType | None
            Traceback of the raised exception, if any.

        Returns
        -------
        None
        """
        await self.close()
