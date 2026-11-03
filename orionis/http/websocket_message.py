"""Provide http operations.

Includes ``WebSocketMessageType``, ``WebSocketState``, ``WebSocketMessage``.
"""

from dataclasses import dataclass
from enum import Enum

class WebSocketMessageType(Enum):
    """Identify a normalized complete WebSocket message."""

    TEXT = "text"
    """Text identifier: ``text``."""
    BYTES = "bytes"
    """Bytes identifier: ``bytes``."""
    DISCONNECT = "disconnect"
    """Disconnect identifier: ``disconnect``."""

class WebSocketState(Enum):
    """Describe the connection lifecycle independently of its server."""

    CONNECTING = "connecting"
    """Connecting identifier: ``connecting``."""
    CONNECTED = "connected"
    """Connected identifier: ``connected``."""
    CLOSING = "closing"
    """Closing identifier: ``closing``."""
    CLOSED = "closed"
    """Closed identifier: ``closed``."""

@dataclass(frozen=True, slots=True, kw_only=True)
class WebSocketMessage:
    """Retain an immutable message without copying its payload."""

    type: WebSocketMessageType
    """Discriminator identifying the message or schema variant."""
    data: str | bytes | None = None
    """Decoded content carried by this message or request."""
    code: int | None = None
    """Machine-readable status or error code."""
    reason: str | None = None
    """Human-readable reason associated with connection closure."""

    def isText(self) -> bool:
        """
        Identify text data.

        Returns
        -------
        bool
            Whether this message contains text.
        """
        return self.type is WebSocketMessageType.TEXT

    def isBytes(self) -> bool:
        """
        Identify binary data.

        Returns
        -------
        bool
            Whether this message contains bytes.
        """
        return self.type is WebSocketMessageType.BYTES

    def isDisconnect(self) -> bool:
        """
        Identify the terminal peer event.

        Returns
        -------
        bool
            Whether this message describes a disconnect.
        """
        return self.type is WebSocketMessageType.DISCONNECT

    @property
    def text(self) -> str:
        """
        Return the original text payload.

        Returns
        -------
        str
            Text payload without a copy.

        Raises
        ------
        TypeError
            If this is not a text message.
        """
        if not self.isText() or not isinstance(self.data, str):
            error_msg = "WebSocket message does not contain text"
            raise TypeError(error_msg)
        return self.data

    @property
    def bytes(self) -> bytes:
        """
        Return the original binary payload.

        Returns
        -------
        bytes
            Binary payload without a copy.

        Raises
        ------
        TypeError
            If this is not a binary message.
        """
        if not self.isBytes() or not isinstance(self.data, bytes):
            error_msg = "WebSocket message does not contain bytes"
            raise TypeError(error_msg)
        return self.data
