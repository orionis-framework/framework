import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING
import msgspec
from orionis.http.enums.status import WebSocketStatus
from orionis.http.exceptions.websocket import WebSocketDisconnected
from orionis.http.websocket_message import WebSocketMessage, WebSocketState

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.adapters.websocket.contracts.transport import IWebSocketTransport
    from orionis.http.payload.estructures.headers import Headers

_DEFAULT_MESSAGE_LIMIT = 1024 * 1024
_MIN_HTTP_ERROR = 400
_MAX_HTTP_ERROR = 599
_MIN_CUSTOM_CLOSE = 3000
_MAX_CUSTOM_CLOSE = 4999
_MAX_CLOSE_REASON = 123
_VALID_CLOSE_CODES = frozenset({
    1000, 1001, 1002, 1003, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014,
})

class WebSocket:
    """Own one server-independent connection with direct awaited messaging."""

    __slots__ = (
        "_accepted", "_adapter", "_close_code", "_close_reason",
        "_connection_state", "_max_message_size", "_params", "_receive_lock",
        "_send_lock", "_state", "_transport",
    )

    def __init__(
        self, transport: IWebSocketTransport, adapter: TransportAdapter, *,
        params: Mapping[str, object] | None = None,
        max_message_size: int = _DEFAULT_MESSAGE_LIMIT,
    ) -> None:
        """
        Bind a normalized transport and connection metadata.

        Parameters
        ----------
        transport : IWebSocketTransport
            Server adapter implementing awaited network operations.
        adapter : TransportAdapter
            Handshake metadata, including normalized proxy information.
        params : Mapping[str, object] | None, optional
            Converted route parameters owned by this connection.
        max_message_size : int, optional
            Positive maximum incoming message size in bytes.

        Returns
        -------
        None
            Prepare a connection awaiting explicit acceptance.

        Raises
        ------
        ValueError
            If the message size limit is not a positive integer.
        """
        if (
            isinstance(max_message_size, bool)
            or not isinstance(max_message_size, int)
            or max_message_size <= 0
        ):
            error_msg = "WebSocket max_message_size must be a positive integer"
            raise ValueError(error_msg)
        self._transport = transport
        self._adapter = adapter
        self._params = dict(params or {})
        self._max_message_size = max_message_size
        self._connection_state = WebSocketState.CONNECTING
        self._accepted = False
        self._close_code = int(WebSocketStatus.ABNORMAL_CLOSURE)
        self._close_reason = ""
        self._send_lock = asyncio.Lock()
        self._receive_lock = asyncio.Lock()
        self._state = SimpleNamespace()

    @property
    def path(self) -> str:
        """
        Return the handshake path.

        Returns
        -------
        str
            Path without query parameters.
        """
        return self._adapter.path() or "/"

    @property
    def headers(self) -> Headers:
        """
        Return handshake headers.

        Returns
        -------
        Headers
            Server supplied header collection.
        """
        return self._adapter.headers()

    @property
    def state(self) -> SimpleNamespace:
        """
        Return connection-local application state.

        Returns
        -------
        SimpleNamespace
            Mutable attributes shared only by this connection's pipeline.
        """
        return self._state

    @property
    def connectionState(self) -> WebSocketState:
        """
        Return the explicit lifecycle state.

        Returns
        -------
        WebSocketState
            Current connection lifecycle phase.
        """
        return self._connection_state

    @property
    def accepted(self) -> bool:
        """
        Report completed or interrupted acceptance.

        Returns
        -------
        bool
            Historical handshake indicator, retained after closure.
        """
        return self._accepted

    @property
    def closed(self) -> bool:
        """
        Report terminal connection closure.

        Returns
        -------
        bool
            True when the connection is terminal.
        """
        return self._connection_state is WebSocketState.CLOSED

    @property
    def supportsCloseDetails(self) -> bool:
        """
        Report support for custom wire close details.

        Returns
        -------
        bool
            True when close codes and reasons can be transmitted.
        """
        return self._transport.supportsCloseDetails

    def routeParams(self) -> dict[str, object]:
        """
        Return mutable connection-local route parameters.

        Returns
        -------
        dict[str, object]
            Converted parameters used by handler injection.
        """
        return self._params

    async def accept(
        self, *, subprotocol: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """
        Accept the pending handshake exactly once.

        Parameters
        ----------
        subprotocol : str | None, optional
            Selected client-offered protocol, when supported by the server.
        headers : Mapping[str, str] | None, optional
            Additional acceptance headers, when supported by the server.

        Returns
        -------
        None
            Open the connection for messaging.

        Raises
        ------
        RuntimeError
            If acceptance or closure already completed.
        WebSocketDisconnected
            If the peer closes during acceptance.
        """
        async with self._send_lock:
            if self._connection_state is not WebSocketState.CONNECTING:
                error_msg = "WebSocket handshake has already completed"
                raise RuntimeError(error_msg)
            try:
                await self._transport.accept(subprotocol=subprotocol, headers=headers)
            except WebSocketDisconnected as exc:
                self._disconnected(exc.code, exc.reason)
                raise
            except asyncio.CancelledError:
                # The acceptance event may already have reached the server.
                self._accepted = True
                self._connection_state = WebSocketState.CLOSING
                raise
            self._accepted = True
            self._connection_state = WebSocketState.CONNECTED

    def _disconnected(self, code: int, reason: str = "") -> None:
        """
        Retain terminal metadata for later operation failures.

        Parameters
        ----------
        code : int
            Observed or locally chosen close code.
        reason : str, optional
            Available close reason.

        Returns
        -------
        None
            Transition to the terminal lifecycle state.
        """
        self._close_code = code
        self._close_reason = reason
        self._connection_state = WebSocketState.CLOSED

    def _requireOpen(self) -> None:
        """
        Reject messaging outside the connected lifecycle state.

        Returns
        -------
        None
            Validate that the handshake completed and closure has not started.

        Raises
        ------
        RuntimeError
            If acceptance has not completed.
        WebSocketDisconnected
            If the connection is closing or closed.
        """
        if (
            self._connection_state is WebSocketState.CLOSING
            or self._connection_state is WebSocketState.CLOSED
        ):
            raise WebSocketDisconnected(self._close_code, self._close_reason)
        if self._connection_state is not WebSocketState.CONNECTED:
            error_msg = "Accept the WebSocket before sending or receiving messages"
            raise RuntimeError(error_msg)

    async def receive(self) -> WebSocketMessage:
        """
        Receive one immutable data or disconnect message.

        Returns
        -------
        WebSocketMessage
            Complete data or terminal peer event, delivered once.

        Raises
        ------
        RuntimeError
            If unaccepted or another receiver is already active.
        WebSocketDisconnected
            If closed, oversized, or the underlying transport disconnects.
        """
        self._requireOpen()
        if self._receive_lock.locked():
            error_msg = "Only one WebSocket receive may run at a time"
            raise RuntimeError(error_msg)
        async with self._receive_lock:
            try:
                message = await self._transport.receive()
            except WebSocketDisconnected as exc:
                self._disconnected(exc.code, exc.reason)
                raise
            if message.isDisconnect():
                self._disconnected(message.code or 1006, message.reason or "")
                return message
            # Closure may race a reader already suspended inside server receive.
            self._requireOpen()
            data = message.data
            if isinstance(data, str):
                size = len(data) if data.isascii() else len(data.encode("utf-8"))
            else:
                size = len(message.bytes)
            if size > self._max_message_size:
                code = WebSocketStatus.MESSAGE_TOO_BIG
                wire_code = code if self.supportsCloseDetails else 1000
                await self.close(wire_code)
                self._disconnected(int(code), "Message too large")
                raise WebSocketDisconnected(int(code), "Message too large")
            return message

    async def _receiveData(self) -> WebSocketMessage:
        """
        Receive data while translating disconnects to exceptions.

        Returns
        -------
        WebSocketMessage
            Text or binary data message.

        Raises
        ------
        WebSocketDisconnected
            If the peer sends its terminal event.
        """
        message = await self.receive()
        if message.isDisconnect():
            raise WebSocketDisconnected(message.code or 1006, message.reason or "")
        return message

    async def receiveText(self) -> str:
        """
        Receive one text payload.

        Returns
        -------
        str
            Original text message.

        Raises
        ------
        TypeError
            If the next message is binary.
        WebSocketDisconnected
            If the connection ends.
        """
        return (await self._receiveData()).text

    async def receiveBytes(self) -> bytes:
        """
        Receive one binary payload.

        Returns
        -------
        bytes
            Original binary message.

        Raises
        ------
        TypeError
            If the next message contains text.
        WebSocketDisconnected
            If the connection ends.
        """
        return (await self._receiveData()).bytes

    async def receiveJson(self) -> object:
        """
        Decode the next text or binary JSON message with msgspec.

        Returns
        -------
        object
            Decoded JSON value.

        Raises
        ------
        msgspec.DecodeError
            If the payload is invalid JSON.
        WebSocketDisconnected
            If the connection ends.
        """
        message = await self._receiveData()
        return msgspec.json.decode(message.text if message.isText() else message.bytes)

    async def send(self, data: str | bytes) -> None:
        """
        Send text or bytes through a serialized, awaited transport write.

        Parameters
        ----------
        data : str | bytes
            Complete message payload.

        Returns
        -------
        None
            Deliver the message while preserving server backpressure.

        Raises
        ------
        TypeError
            If data is neither text nor bytes.
        WebSocketDisconnected
            If the peer closes before delivery.
        """
        if not isinstance(data, (str, bytes)):
            error_msg = "WebSocket messages must be str or bytes"
            raise TypeError(error_msg)
        async with self._send_lock:
            self._requireOpen()
            try:
                if isinstance(data, str):
                    await self._transport.sendText(data)
                else:
                    await self._transport.sendBytes(data)
            except WebSocketDisconnected as exc:
                self._disconnected(exc.code, exc.reason)
                raise
            except asyncio.CancelledError:
                # A cancelled write may have sent only part of its frame.
                self._connection_state = WebSocketState.CLOSING
                raise

    async def sendText(self, data: str) -> None:
        """
        Send one text message with natural backpressure.

        Parameters
        ----------
        data : str
            Complete text payload.

        Returns
        -------
        None
            Await the serialized write.

        Raises
        ------
        TypeError
            If the payload is not text.
        """
        if not isinstance(data, str):
            error_msg = "WebSocket text payload must be str"
            raise TypeError(error_msg)
        await self.send(data)

    async def sendBytes(self, data: bytes) -> None:
        """
        Send one binary message without copying the payload.

        Parameters
        ----------
        data : bytes
            Complete binary payload.

        Returns
        -------
        None
            Await the serialized write.

        Raises
        ------
        TypeError
            If the payload is not bytes.
        """
        if not isinstance(data, bytes):
            error_msg = "WebSocket binary payload must be bytes"
            raise TypeError(error_msg)
        await self.send(data)

    async def sendJson(self, data: object) -> None:
        """
        Encode a JSON value and send one UTF-8 text message.

        Parameters
        ----------
        data : object
            JSON-serializable value.

        Returns
        -------
        None
            Await delivery of the msgspec encoded payload.
        """
        await self.sendText(msgspec.json.encode(data).decode("utf-8"))

    async def reject(self, status_code: int = 403) -> None:
        """
        Reject the pending handshake once.

        Parameters
        ----------
        status_code : int, optional
            HTTP error status when supported by the server.

        Returns
        -------
        None
            Finish handshake denial; repeated calls do nothing.

        Raises
        ------
        RuntimeError
            If acceptance was already attempted.
        ValueError
            If the status is not an HTTP error code.
        """
        if (
            isinstance(status_code, bool) or not isinstance(status_code, int)
            or not _MIN_HTTP_ERROR <= status_code <= _MAX_HTTP_ERROR
        ):
            error_msg = "WebSocket rejection status must be between 400 and 599"
            raise ValueError(error_msg)
        async with self._send_lock:
            if self.closed:
                return
            if self._connection_state is not WebSocketState.CONNECTING:
                error_msg = "Cannot reject an accepted WebSocket"
                raise RuntimeError(error_msg)
            self._connection_state = WebSocketState.CLOSING
            try:
                await self._transport.reject(status_code)
            finally:
                self._disconnected(int(WebSocketStatus.POLICY_VIOLATION))

    async def close(
        self, code: WebSocketStatus | int = WebSocketStatus.NORMAL_CLOSURE,
        reason: str = "",
    ) -> None:
        """
        Close an accepted connection or reject a pending handshake once.

        Parameters
        ----------
        code : WebSocketStatus | int, optional
            Valid wire close code.
        reason : str, optional
            Close reason bounded to 123 UTF-8 bytes.

        Returns
        -------
        None
            Complete closure; repeated calls do nothing.

        Raises
        ------
        ValueError
            If the code or reason is invalid.
        NotImplementedError
            If the transport cannot transmit custom close details.
        """
        if self.closed:
            return
        if (
            isinstance(code, bool) or not isinstance(code, int)
            or (code not in _VALID_CLOSE_CODES
                and not _MIN_CUSTOM_CLOSE <= code <= _MAX_CUSTOM_CLOSE)
            or not isinstance(reason, str)
            or len(reason.encode("utf-8")) > _MAX_CLOSE_REASON
        ):
            error_msg = "Invalid WebSocket close code or reason"
            raise ValueError(error_msg)
        async with self._send_lock:
            if self.closed:
                return
            pending = self._connection_state is WebSocketState.CONNECTING
            if (
                not pending and not self.supportsCloseDetails
                and (code != WebSocketStatus.NORMAL_CLOSURE or reason)
            ):
                error_msg = "Transport does not expose WebSocket close code or reason"
                raise NotImplementedError(error_msg)
            self._connection_state = WebSocketState.CLOSING
            try:
                if pending:
                    await self._transport.reject()
                else:
                    await self._transport.close(int(code), reason)
            finally:
                self._disconnected(int(code), reason)

    def __aiter__(self) -> WebSocket:
        """
        Iterate data messages until the peer disconnects.

        Returns
        -------
        WebSocket
            This connection as a single-consumer async iterator.
        """
        return self

    async def __anext__(self) -> WebSocketMessage:
        """
        Receive the next application message for asynchronous iteration.

        Returns
        -------
        WebSocketMessage
            Next text or binary message.

        Raises
        ------
        StopAsyncIteration
            If connection closure is observed.
        """
        try:
            message = await self.receive()
        except WebSocketDisconnected:
            raise StopAsyncIteration from None
        if message.isDisconnect():
            raise StopAsyncIteration
        return message
