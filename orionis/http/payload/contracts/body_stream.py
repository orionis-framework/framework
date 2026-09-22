from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

class IBodyStream(ABC):
    """
    Define the minimal contract for reading an HTTP request body.

    Notes
    -----
    Both ``stream()`` and ``read()`` must be safe to call multiple
    times once the body has been fully buffered.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def isBuffered(self) -> bool:
        """
        Return ``True`` when the full body has been cached by ``read()``.

        Returns
        -------
        bool
            ``True`` if the body has been fully buffered,
            ``False`` otherwise.
        """

    @property
    @abstractmethod
    def isConsumed(self) -> bool:
        """
        Return ``True`` when the raw transport stream has been consumed.

        Returns
        -------
        bool
            ``True`` if the transport stream has been iterated,
            ``False`` otherwise.
        """

    @abstractmethod
    async def stream(self) -> AsyncGenerator[bytes]:  # NOSONAR
        """
        Yield successive byte chunks from the request body.

        Implementations must replay from the internal buffer when
        ``read()`` was called first, so streaming consumers (e.g.
        multipart parsers) still work after a plain ``body()`` call.

        Yields
        ------
        bytes
            A chunk of the raw request body.

        Raises
        ------
        RuntimeError
            If the stream was consumed by a streaming consumer before
            the body was buffered.
        PayloadTooLargeException
            If incoming data exceeds the configured body-size limit.
        """

    @abstractmethod
    async def read(self) -> bytes:
        """
        Buffer and return the full request body.  Idempotent.

        Implementations must cache the result so repeated calls return
        the same bytes object without re-reading the transport.

        Returns
        -------
        bytes
            Complete body as a contiguous bytes object.
        """
