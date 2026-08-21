from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

class IStorageStream(ABC):
    """
    Define the contract for an asynchronous binary stream handle.

    Implementations wrap an underlying binary handle (local file,
    in-memory buffer, remote object) and expose non-blocking read,
    write, and seek operations. Streams are async context managers::

        async with file.open("rb") as stream:
            chunk = await stream.read(65536)
    """

    __slots__ = ()

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def close(self) -> None:
        """
        Flush pending data and release the underlying handle.

        Returns
        -------
        None
        """

    @abstractmethod
    async def __aenter__(self) -> IStorageStream:
        """
        Open the underlying handle and return the stream.

        Returns
        -------
        IStorageStream
            The stream itself, ready for I/O operations.
        """

    @abstractmethod
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
