from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from orionis.storage.contracts.stream import IStorageStream

if TYPE_CHECKING:
    from collections.abc import Callable
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

    __slots__ = ("_handle", "_on_close", "_opener")

    def __init__(
        self,
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

    async def __ensureHandle(self) -> BinaryIO:
        """
        Open the underlying handle on first use and return it.

        Returns
        -------
        BinaryIO
            The open binary handle backing this stream.
        """
        # Open lazily so building the stream object stays side-effect free.
        if self._handle is None:
            self._handle = await asyncio.to_thread(self._opener)
        return self._handle

    async def read(self, size: int = -1) -> bytes:
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
        handle = await self.__ensureHandle()
        return await asyncio.to_thread(handle.read, size)

    async def write(self, data: bytes) -> int:
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
        handle = await self.__ensureHandle()
        return await asyncio.to_thread(handle.write, data)

    async def seek(self, offset: int, whence: int = 0) -> int:
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
        handle = await self.__ensureHandle()
        return await asyncio.to_thread(handle.seek, offset, whence)

    async def close(self) -> None:
        """
        Flush pending data and release the underlying handle.

        Invokes the *on_close* callback (when provided) before closing
        the handle. Closing an unopened or already closed stream is a
        no-op.

        Returns
        -------
        None
        """
        handle = self._handle
        if handle is None:
            return

        # Detach first so double-close attempts become harmless no-ops.
        self._handle = None
        if self._on_close is not None:
            await asyncio.to_thread(self._on_close, handle)
        await asyncio.to_thread(handle.close)

    async def __aenter__(self) -> IStorageStream:
        """
        Open the underlying handle and return the stream.

        Returns
        -------
        IStorageStream
            The stream itself, ready for I/O operations.
        """
        await self.__ensureHandle()
        return self

    async def __aexit__(
        self,
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
