from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.payload.uploaded_file import UploadedFile

class IMultipartPart(ABC):
    """
    Define the contract for a single part within a multipart HTTP request body.

    Implementations parse MIME headers, accumulate raw bytes, and finalize
    the part into either a decoded string or an ``UploadedFile`` handle.
    """

    __slots__ = ()

    @abstractmethod
    def write(self, chunk: bytes | bytearray | memoryview) -> None:
        """
        Append *chunk* to this part's data buffer.

        Parameters
        ----------
        chunk : bytes
            Raw bytes received from the multipart stream.

        Returns
        -------
        None
            Accumulates bytes in the internal buffer; no value returned.
        """

    @abstractmethod
    def finalize(self) -> UploadedFile | str:
        """
        Return this part's content in its final form.

        Returns
        -------
        UploadedFile | str
            The ``UploadedFile`` handle for file parts, or the decoded
            string for field parts.
        """
