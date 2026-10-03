from dataclasses import dataclass
from enum import Enum

class WebSocketMessageType(Enum):
    """Identify a normalized complete WebSocket message."""

    TEXT = "text"
    BYTES = "bytes"
    DISCONNECT = "disconnect"

class WebSocketState(Enum):
    """Describe the connection lifecycle independently of its server."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    CLOSING = "closing"
    CLOSED = "closed"

@dataclass(frozen=True, slots=True, kw_only=True)
class WebSocketMessage:
    """Retain an immutable message without copying its payload."""

    type: WebSocketMessageType
    data: str | bytes | None = None
    code: int | None = None
    reason: str | None = None

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
