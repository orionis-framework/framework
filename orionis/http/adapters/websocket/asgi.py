from typing import TYPE_CHECKING
from orionis.http.adapters.websocket.contracts.transport import IWebSocketTransport
from orionis.http.exceptions.websocket import WebSocketDisconnected
from orionis.http.websocket_message import WebSocketMessage, WebSocketMessageType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

_HEADERS_VERSION = (2, 1)
_REASON_VERSION = (2, 3)
_HEADER_NAME_CHARACTERS = frozenset(
    "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyz",
)

class ASGIWebSocketTransport(IWebSocketTransport):
    """Translate the ASGI WebSocket protocol into normalized operations."""

    __slots__ = ("_handshake_received", "_receive", "_scope", "_send", "_version")

    def __init__(
        self, scope: dict, receive: Callable[[], Awaitable[dict]],
        send: Callable[[dict], Awaitable[None]],
    ) -> None:
        """
        Retain callbacks and advertised WebSocket specification version.

        Parameters
        ----------
        scope : dict
            Original ASGI connection scope.
        receive : Callable
            Server event reader.
        send : Callable
            Server event writer.

        Returns
        -------
        None
            Prepare the pending handshake.
        """
        self._scope = scope
        self._receive = receive
        self._send = send
        self._handshake_received = False
        version = scope.get("asgi", {}).get("spec_version", "2.0")
        self._version = tuple(int(part) for part in version.split("."))

    async def _connectEvent(self) -> None:
        """
        Consume the server's initial handshake event once.

        Returns
        -------
        None
            Validate that the peer is awaiting acceptance.

        Raises
        ------
        WebSocketDisconnected
            If the peer disconnects before acceptance.
        RuntimeError
            If the server supplies an invalid initial event.
        """
        if self._handshake_received:
            return
        event = await self._receive()
        if event.get("type") == "websocket.disconnect":
            raise WebSocketDisconnected(
                event.get("code", 1006), event.get("reason") or "",
            )
        if event.get("type") != "websocket.connect":
            error_msg = "Expected websocket.connect before the handshake"
            raise RuntimeError(error_msg)
        self._handshake_received = True

    def _acceptHeaders(
        self, headers: Mapping[str, str] | None,
    ) -> list[tuple[bytes, bytes]]:
        """
        Validate and encode handshake headers before sending any event.

        Parameters
        ----------
        headers : Mapping[str, str] | None
            User supplied response headers.

        Returns
        -------
        list[tuple[bytes, bytes]]
            Encoded lowercase header pairs.

        Raises
        ------
        NotImplementedError
            If the server predates ASGI HTTP 2.1.
        ValueError
            If a header violates the handshake header rules.
        """
        if not headers:
            return []
        if self._version < _HEADERS_VERSION:
            error_msg = "WebSocket accept headers require ASGI HTTP spec 2.1"
            raise NotImplementedError(error_msg)
        result = []
        for raw_name, value in headers.items():
            name = raw_name.lower()
            if (
                not name or any(char not in _HEADER_NAME_CHARACTERS for char in name)
                or name == "sec-websocket-protocol"
                or any(char in value for char in "\r\n\x00")
            ):
                error_msg = "Invalid WebSocket acceptance header"
                raise ValueError(error_msg)
            result.append((name.encode("ascii"), value.encode("latin-1")))
        return result

    async def accept(
        self, *, subprotocol: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """
        Accept using the server's supported handshake fields.

        Parameters
        ----------
        subprotocol : str | None, optional
            Subprotocol offered by the client.
        headers : Mapping[str, str] | None, optional
            Additional headers supported since ASGI HTTP 2.1.

        Returns
        -------
        None
            Await server acceptance.

        Raises
        ------
        ValueError
            If the selected subprotocol was not offered.
        WebSocketDisconnected
            If the peer disappears during acceptance.
        """
        if (
            subprotocol is not None
            and subprotocol not in self._scope.get("subprotocols", ())
        ):
            error_msg = "Selected WebSocket subprotocol was not offered by the client"
            raise ValueError(error_msg)
        encoded_headers = self._acceptHeaders(headers)
        event: dict = {"type": "websocket.accept"}
        if subprotocol is not None:
            event["subprotocol"] = subprotocol
        if encoded_headers:
            event["headers"] = encoded_headers
        try:
            await self._connectEvent()
            await self._send(event)
        except OSError as exc:
            raise WebSocketDisconnected from exc

    async def receive(self) -> WebSocketMessage:
        """
        Normalize one complete ASGI data or disconnect event.

        Returns
        -------
        WebSocketMessage
            The payload or peer closure details.

        Raises
        ------
        RuntimeError
            If the server supplies an invalid event or two payloads.
        WebSocketDisconnected
            If a transport read raises an operating system error.
        """
        try:
            event = await self._receive()
        except OSError as exc:
            raise WebSocketDisconnected from exc
        if event.get("type") == "websocket.disconnect":
            return WebSocketMessage(
                type=WebSocketMessageType.DISCONNECT,
                code=event.get("code", 1006), reason=event.get("reason") or "",
            )
        if event.get("type") == "websocket.receive":
            text, data = event.get("text"), event.get("bytes")
            if isinstance(text, str) and data is None:
                return WebSocketMessage(type=WebSocketMessageType.TEXT, data=text)
            if isinstance(data, bytes) and text is None:
                return WebSocketMessage(type=WebSocketMessageType.BYTES, data=data)
        error_msg = "Unexpected WebSocket receive event"
        raise RuntimeError(error_msg)

    async def sendText(self, data: str) -> None:
        """
        Send one text message and await server backpressure.

        Parameters
        ----------
        data : str
            Text payload.

        Returns
        -------
        None
            Finish the transport write.

        Raises
        ------
        WebSocketDisconnected
            If the peer has closed the connection.
        """
        try:
            await self._send({"type": "websocket.send", "text": data})
        except OSError as exc:
            raise WebSocketDisconnected from exc

    async def sendBytes(self, data: bytes) -> None:
        """
        Send one binary message and await server backpressure.

        Parameters
        ----------
        data : bytes
            Binary payload.

        Returns
        -------
        None
            Finish the transport write.

        Raises
        ------
        WebSocketDisconnected
            If the peer has closed the connection.
        """
        try:
            await self._send({"type": "websocket.send", "bytes": data})
        except OSError as exc:
            raise WebSocketDisconnected from exc

    async def reject(self, status_code: int = 403) -> None:
        """
        Deny the handshake with an HTTP status when the extension exists.

        Parameters
        ----------
        status_code : int, optional
            Rejection status; servers without the extension always use 403.

        Returns
        -------
        None
            Finish the denial exchange.

        Raises
        ------
        WebSocketDisconnected
            If the peer closes while rejection is sent.
        """
        try:
            await self._connectEvent()
            if "websocket.http.response" in self._scope.get("extensions", {}):
                await self._send({
                    "type": "websocket.http.response.start",
                    "status": status_code, "headers": [],
                })
                await self._send({
                    "type": "websocket.http.response.body", "body": b"",
                })
            else:
                await self._send({"type": "websocket.close", "code": 1008})
        except OSError as exc:
            raise WebSocketDisconnected from exc

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """
        Send a close event using fields supported by the advertised version.

        Parameters
        ----------
        code : int, optional
            Valid WebSocket close code.
        reason : str, optional
            Reason sent on servers supporting ASGI HTTP 2.3 or later.

        Returns
        -------
        None
            Await the close event delivery.

        Raises
        ------
        WebSocketDisconnected
            If the peer closes before the event reaches the server.
        """
        event: dict = {"type": "websocket.close", "code": code}
        if self._version >= _REASON_VERSION:
            event["reason"] = reason
        try:
            await self._send(event)
        except OSError as exc:
            raise WebSocketDisconnected from exc
