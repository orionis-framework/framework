from typing import TYPE_CHECKING
from granian._granian import RSGIProtocolClosed
from granian.rsgi import WebsocketMessageType
from orionis.http.adapters.websocket.contracts.transport import IWebSocketTransport
from orionis.http.exceptions.websocket import WebSocketDisconnected
from orionis.http.websocket_message import WebSocketMessage, WebSocketMessageType

if TYPE_CHECKING:
    from collections.abc import Mapping
    from granian._granian import RSGIWebsocketProtocol, RSGIWebsocketTransport

_NORMAL_CLOSE = 1000

class RSGIWebSocketTransport(IWebSocketTransport):
    """Adapt Granian's actual RSGI WebsocketProtocol and accepted transport."""

    __slots__ = ("_protocol", "_transport")

    def __init__(self, protocol: RSGIWebsocketProtocol) -> None:
        """
        Retain the pending server protocol.

        Parameters
        ----------
        protocol : WebsocketProtocol
            Granian's handshake and close interface.

        Returns
        -------
        None
            Prepare a transport that will be bound during acceptance.
        """
        self._protocol = protocol
        self._transport: RSGIWebsocketTransport | None = None

    @property
    def supportsCloseDetails(self) -> bool:
        """
        Report the documented RSGI close-frame limitation.

        Returns
        -------
        bool
            False because ``protocol.close(status)`` controls HTTP rejection.
        """
        return False

    async def accept(
        self, *, subprotocol: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """
        Accept through Granian's argument-free handshake method.

        Parameters
        ----------
        subprotocol : str | None, optional
            Unsupported by this RSGI version.
        headers : Mapping[str, str] | None, optional
            Unsupported by this RSGI version.

        Returns
        -------
        None
            Store the returned accepted transport.

        Raises
        ------
        NotImplementedError
            If unsupported handshake options are requested.
        WebSocketDisconnected
            If the server reports an already closed connection.
        """
        if subprotocol is not None or headers:
            error_msg = "RSGI does not expose WebSocket accept headers or subprotocols"
            raise NotImplementedError(error_msg)
        try:
            self._transport = await self._protocol.accept()
        except (OSError, RSGIProtocolClosed) as exc:
            raise WebSocketDisconnected from exc

    def _acceptedTransport(self) -> RSGIWebsocketTransport:
        """
        Require the transport returned by a completed handshake.

        Returns
        -------
        RSGIWebsocketTransport
            Granian's active message transport.

        Raises
        ------
        RuntimeError
            If called before acceptance completed.
        """
        if self._transport is None:
            error_msg = "RSGI WebSocket transport has not been accepted"
            raise RuntimeError(error_msg)
        return self._transport

    async def receive(self) -> WebSocketMessage:
        """
        Normalize Granian's close, bytes and string message kinds.

        Returns
        -------
        WebSocketMessage
            Message with unknown peer close details represented as code 1006.

        Raises
        ------
        RuntimeError
            If the server supplies an invalid message kind or payload.
        WebSocketDisconnected
            If the server reports a transport disconnection.
        """
        try:
            event = await self._acceptedTransport().receive()
        except (OSError, RSGIProtocolClosed) as exc:
            raise WebSocketDisconnected from exc
        if event.kind == WebsocketMessageType.close:
            return WebSocketMessage(type=WebSocketMessageType.DISCONNECT, code=1006)
        if event.kind == WebsocketMessageType.bytes and isinstance(event.data, bytes):
            return WebSocketMessage(type=WebSocketMessageType.BYTES, data=event.data)
        if event.kind == WebsocketMessageType.string and isinstance(event.data, str):
            return WebSocketMessage(type=WebSocketMessageType.TEXT, data=event.data)
        error_msg = "Unexpected RSGI WebSocket receive event"
        raise RuntimeError(error_msg)

    async def sendText(self, data: str) -> None:
        """
        Await Granian's text write without buffering.

        Parameters
        ----------
        data : str
            Complete text message.

        Returns
        -------
        None
            Finish the server write.

        Raises
        ------
        WebSocketDisconnected
            If the peer has closed the transport.
        """
        try:
            await self._acceptedTransport().send_str(data)
        except (OSError, RSGIProtocolClosed) as exc:
            raise WebSocketDisconnected from exc

    async def sendBytes(self, data: bytes) -> None:
        """
        Await Granian's binary write without buffering.

        Parameters
        ----------
        data : bytes
            Complete binary message.

        Returns
        -------
        None
            Finish the server write.

        Raises
        ------
        WebSocketDisconnected
            If the peer has closed the transport.
        """
        try:
            await self._acceptedTransport().send_bytes(data)
        except (OSError, RSGIProtocolClosed) as exc:
            raise WebSocketDisconnected from exc

    async def reject(self, status_code: int = 403) -> None:
        """
        Reject the handshake using the actual HTTP status argument.

        Parameters
        ----------
        status_code : int, optional
            HTTP rejection status.

        Returns
        -------
        None
            Invoke Granian's synchronous close method.
        """
        self._protocol.close(status_code)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """
        Close through Granian's default connection closure API.

        Parameters
        ----------
        code : int, optional
            Only normal closure is supported.
        reason : str, optional
            Only the empty reason is supported.

        Returns
        -------
        None
            Invoke synchronous connection closure.

        Raises
        ------
        NotImplementedError
            If a custom wire close code or reason is requested.
        """
        if code != _NORMAL_CLOSE or reason:
            error_msg = "RSGI does not expose WebSocket close frame code or reason"
            raise NotImplementedError(error_msg)
        self._protocol.close(None)
