from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

class IUploadedFile(ABC):
    """
    Define the contract for an uploaded file held in memory or on disk.

    Implementations buffer incoming bytes via ``write()``, optionally
    spill to a temporary file, and expose content through ``read()``
    and ``save()``.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def size(self) -> int:
        """
        Return the total number of bytes written so far.

        Returns
        -------
        int
            Cumulative byte count across all ``write`` calls.
        """

    @property
    @abstractmethod
    def extension(self) -> str:
        """
        Return the file extension derived from *filename*, in lowercase.

        Returns
        -------
        str
            Lowercase suffix including the leading dot (e.g. ``".png"``).
            Empty string if the filename has no extension.
        """

    @abstractmethod
    def write(self, chunk: bytes | bytearray | memoryview) -> None:
        """
        Append *chunk* to the file buffer.

        Append at the end even when a previous read moved the cursor.

        Parameters
        ----------
        chunk : bytes | bytearray | memoryview
            Raw bytes to append.

        Returns
        -------
        None
        """

    @abstractmethod
    def read(self) -> bytes:
        """
        Read the entire file content from the beginning.

        Returns
        -------
        bytes
            Full file contents.
        """

    @abstractmethod
    def chunks(self, size: int = 65536) -> Iterator[bytes]:
        """
        Iterate over the file content in fixed-size chunks.

        Parameters
        ----------
        size : int
            Maximum number of bytes per yielded chunk.

        Returns
        -------
        Iterator[bytes]
            Iterator yielding consecutive chunks from the beginning
            of the buffered content.
        """

    @abstractmethod
    def replace(self, data: bytes) -> None:
        """
        Replace the file content with *data* and update the byte counter.

        Parameters
        ----------
        data : bytes
            New file content that replaces previously written data.

        Returns
        -------
        None
        """

    @abstractmethod
    def save(self, path: str | Path) -> None:
        """
        Write the file contents to *path* on the local filesystem.

        Parameters
        ----------
        path : str or Path
            Destination path for the saved file.

        Returns
        -------
        None
        """

    @abstractmethod
    def close(self) -> None:
        """
        Close the file handle and release all associated resources.

        Returns
        -------
        None
        """
