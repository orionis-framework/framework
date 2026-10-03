from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.foundation.config.http.entitites.body import HTTPBodyLimits
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.contracts.body_stream import IBodyStream

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

class PayloadTooLargeException(ValueError):
    """Raise when the request body exceeds the configured size limit."""

class BodyStream(IBodyStream):
    """
    Own and manage the raw HTTP request body stream.

    Enforce the max-body-size limit and provide transparent replay
    when the body has already been buffered by ``read()``.

    Notes
    -----
    The underlying transport stream is consumed **at most once**.
    After ``read()`` completes, ``stream()`` replays the cached
    buffer so callers such as the multipart parser keep working
    even after a plain ``body()`` call.
    Calling ``stream()`` after a streaming consumer has iterated
    it—without a prior ``read()``—raises ``RuntimeError``.
    Raw bytes are gone after streaming multipart.
    """

    __slots__ = (
        "__body",
        "__consumed",
        "__is_rsgi",
        "__max_buffer_size",
        "__max_size",
        "__receive",
    )

    def __init__(
        self,
        interface: Interface,
        receive_or_protocol: object,
        max_body_size: int | None = HTTPBodyLimits.max_body_size,
        *,
        max_buffer_size: int | None = HTTPBodyLimits.max_buffer_size,
    ) -> None:
        """
        Initialize a BodyStream for the given transport interface.

        Parameters
        ----------
        interface : Interface
            Transport protocol type (ASGI or RSGI).
        receive_or_protocol : object
            ASGI receive callable or RSGI ``HTTPProtocol`` instance.
        max_body_size : int | None, optional
            Maximum allowed body size in bytes (default 16 MiB). An explicit
            ``None`` disables the transport limit for a manually built stream.
        max_buffer_size : int | None, optional
            Maximum bytes buffered by read() (default 2 MiB). An explicit
            ``None`` disables this limit for a manually built stream.

        Returns
        -------
        None
        """
        # Initialize the body buffer to None (not yet read).
        self.__body: bytes | None = None
        # Track whether the raw transport stream has been consumed.
        self.__consumed: bool = False
        # Record which transport provides the body chunks.
        self.__is_rsgi: bool = interface is Interface.RSGI
        for name, value in (
            ("max_body_size", max_body_size), ("max_buffer_size", max_buffer_size),
        ):
            if value is not None:
                if not isinstance(value, int) or isinstance(value, bool):
                    error_msg = f"{name} must be an integer or None."
                    raise TypeError(error_msg)
                if value < 0:
                    error_msg = f"{name} must not be negative."
                    raise ValueError(error_msg)
        self.__max_size = max_body_size
        self.__max_buffer_size = max_buffer_size
        # Store the receive callable or RSGI protocol reference.
        self.__receive = receive_or_protocol

    @property
    def isBuffered(self) -> bool:
        """
        Return ``True`` when the full body has been cached by ``read()``.

        Returns
        -------
        bool
            ``True`` if the body has been fully buffered,
            ``False`` otherwise.
        """
        return self.__body is not None

    @property
    def isConsumed(self) -> bool:
        """
        Return ``True`` when the raw transport stream has been consumed.

        Returns
        -------
        bool
            ``True`` if the transport stream has been iterated,
            ``False`` otherwise.
        """
        return self.__consumed

    async def stream(self) -> AsyncGenerator[bytes]:  # NOSONAR # noqa: C901
        """
        Yield body chunks from the transport.

        Replay the internal buffer as a single chunk when ``read()``
        was called first, making this method safe to call multiple times.

        Yields
        ------
        bytes
            A chunk of the raw request body.

        Raises
        ------
        RuntimeError
            If the stream was consumed by a streaming consumer
            (e.g. multipart) before the body was buffered.
        PayloadTooLargeException
            If incoming data exceeds ``max_body_size``.
        """
        # Replay from buffer when the body has already been read.
        if self.__body is not None:
            yield self.__body
            return

        # Guard against double-consumption of the raw transport stream.
        if self.__consumed:
            error_msg = "Request stream already consumed"
            raise RuntimeError(error_msg)

        # Mark the stream consumed before iterating to prevent re-entry.
        self.__consumed = True
        total = 0
        # Apply the configured limit to the accumulated byte count.
        max_size = self.__max_size

        # RSGI (Granian): iterate the protocol object directly.
        if self.__is_rsgi:
            async for chunk in self.__receive:
                if not chunk:
                    continue
                total += len(chunk)
                if max_size is not None and total > max_size:
                    error_msg = "Request body too large"
                    raise PayloadTooLargeException(error_msg)
                yield chunk
            return

        # ASGI: poll the receive callable until more_body is False.
        while True:
            message = await self.__receive()
            chunk = message.get("body", b"")
            if chunk:
                total += len(chunk)
                if max_size is not None and total > max_size:
                    error_msg = "Request body too large"
                    raise PayloadTooLargeException(error_msg)
                yield chunk
            if not message.get("more_body", False):
                break

    async def read(self) -> bytes:
        """
        Buffer and return the full request body.  Idempotent.

        Subsequent calls return the cached buffer without re-reading
        the transport.

        Returns
        -------
        bytes
            Complete request body as a contiguous bytes object.

        Raises
        ------
        RuntimeError
            If the stream was consumed by a streaming consumer
            without having been buffered first.
        PayloadTooLargeException
            If the body exceeds ``max_body_size`` or ``max_buffer_size``.
        """
        # Return the cached buffer immediately if already read.
        body = self.__body
        if body is not None:
            return body

        # Collect the transport chunks into the complete body buffer.
        buffer = bytearray()
        async for chunk in self.stream():
            if (
                self.__max_buffer_size is not None
                and len(buffer) + len(chunk) > self.__max_buffer_size
            ):
                error_msg = "Request body exceeds the buffering limit"
                raise PayloadTooLargeException(error_msg)
            buffer.extend(chunk)
        self.__body = bytes(buffer)
        return self.__body
