from __future__ import annotations
import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING
import msgspec
from granian.rsgi import ProtocolClosed, ProtocolError
from orionis.http.enums.interfaces import Interface

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping
    from granian.rsgi import WebsocketProtocol
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.payload.estructures.headers import Headers

_DISCONNECTED = (OSError, ProtocolClosed, ProtocolError)
_DEFAULT_MESSAGE_LIMIT = 1024 * 1024
_NORMAL_CLOSE = 1000
_MESSAGE_TOO_BIG = 1009
_MIN_HTTP_ERROR = 400
_MAX_HTTP_ERROR = 599
_MIN_CUSTOM_CLOSE = 3000
_MAX_CUSTOM_CLOSE = 4999
_MAX_CLOSE_REASON = 123

class WebSocketDisconnected(RuntimeError):
    """Report a closed peer connection to an application handler."""

    def __init__(self, code: int = 1006, reason: str = "") -> None:
        """Store peer close details.

        Parameters
        ----------
        code : int, optional
            Peer close code, or 1006 when unavailable from the transport.
        reason : str, optional
            Peer close reason when available.

        Returns
        -------
        None
            Initialize the exception.
        """
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket disconnected ({code}): {reason}")

class WebSocket:
    """Expose one connection with explicit acceptance and awaited messaging."""

    __slots__ = (
        "_adapter", "_closed", "_connected", "_handshake_received", "_interface",
        "_max_message_size",
        "_params", "_protocol", "_receive", "_receive_lock", "_send",
        "_send_lock", "_state", "_transport",
    )

    def __init__(  # noqa: PLR0913 - Protocol callbacks and connection limits.
        self,
        interface: Interface,
        adapter: TransportAdapter,
        receive_or_protocol: Callable[[], Awaitable[dict]] | WebsocketProtocol,
        send: Callable[[dict], Awaitable[None]] | None = None,
        *,
        params: Mapping[str, object] | None = None,
        max_message_size: int = _DEFAULT_MESSAGE_LIMIT,
    ) -> None:
        """Bind connection metadata and the protocol callbacks.

        Parameters
        ----------
        interface : Interface
            ASGI or RSGI protocol identifier.
        adapter : TransportAdapter
            Handshake metadata, including normalized proxy information.
        receive_or_protocol : Callable | WebsocketProtocol
            ASGI receive callback or Granian WebsocketProtocol.
        send : Callable | None, optional
            ASGI send callback; omitted for RSGI.
        params : Mapping[str, object] | None, optional
            Converted route parameters owned by this connection.
        max_message_size : int, optional
            Maximum incoming message bytes; defaults to one MiB.

        Returns
        -------
        None
            Prepare an unaccepted connection.

        Raises
        ------
        ValueError
            If the message limit is not a positive integer.
        """
        if (
            isinstance(max_message_size, bool)
            or not isinstance(max_message_size, int)
            or max_message_size <= 0
        ):
            error_msg = "WebSocket max_message_size must be a positive integer"
            raise ValueError(error_msg)
        self._interface = interface
        self._adapter = adapter
        self._receive = receive_or_protocol if interface is Interface.ASGI else None
        self._protocol = receive_or_protocol if interface is Interface.RSGI else None
        self._send = send
        self._transport = None
        self._params = dict(params or {})
        self._max_message_size = max_message_size
        self._connected = False
        self._handshake_received = False
        self._closed = False
        self._send_lock = asyncio.Lock()
        self._receive_lock = asyncio.Lock()
        self._state = SimpleNamespace()

    @property
    def path(self) -> str:
        """Return the handshake path.

        Returns
        -------
        str
            Path without query parameters.
        """
        return self._adapter.path() or "/"

    @property
    def headers(self) -> Headers:
        """Return handshake headers.

        Returns
        -------
        Headers
            Header collection supplied by the server.
        """
        return self._adapter.headers()

    @property
    def state(self) -> SimpleNamespace:
        """Return mutable connection-local application state.

        Returns
        -------
        SimpleNamespace
            Attributes shared only by this connection's pipeline.
        """
        return self._state

    @property
    def accepted(self) -> bool:
        """Return whether the handshake was accepted.

        Returns
        -------
        bool
            True after successful acceptance, including after closure.
        """
        return self._connected

    @property
    def closed(self) -> bool:
        """Return whether the connection has closed or disconnected.

        Returns
        -------
        bool
            True when further application messages are forbidden.
        """
        return self._closed

    def routeParams(self) -> dict[str, object]:
        """Return mutable connection-local path parameters.

        Returns
        -------
        dict[str, object]
            Converted parameters used by handler injection.
        """
        return self._params

    async def _connectEvent(self) -> None:
        """Consume the ASGI handshake notification.

        Returns
        -------
        None
            Validate the initial server event.

        Raises
        ------
        WebSocketDisconnected
            If the peer closed during the handshake.
        RuntimeError
            If the server did not supply a connect event.
        """
        if self._handshake_received:
            return
        event = await self._receive()
        if event["type"] == "websocket.disconnect":
            self._closed = True
            raise WebSocketDisconnected(event.get("code", 1006))
        if event["type"] != "websocket.connect":
            error_msg = "Expected websocket.connect before the handshake"
            raise RuntimeError(error_msg)
        self._handshake_received = True

    async def accept(self) -> None:
        """Accept the pending handshake exactly once.

        Returns
        -------
        None
            Open the connection for messaging.

        Raises
        ------
        RuntimeError
            If the connection was accepted or closed already.
        WebSocketDisconnected
            If the transport closes during acceptance.
        """
        async with self._send_lock:
            if self._connected or self._closed:
                error_msg = "WebSocket handshake has already completed"
                raise RuntimeError(error_msg)
            try:
                if self._interface is Interface.ASGI:
                    await self._connectEvent()
                    self._connected = True
                    await self._send({"type": "websocket.accept"})
                else:
                    self._connected = True
                    self._transport = await self._protocol.accept()
            except _DISCONNECTED as exc:
                self._closed = True
                raise WebSocketDisconnected from exc
            self._connected = True

    def _requireOpen(self) -> None:
        """Reject operations before acceptance or after closure.

        Returns
        -------
        None
            Validate the messaging state.

        Raises
        ------
        RuntimeError
            If the handshake has not been accepted.
        WebSocketDisconnected
            If the connection is closed.
        """
        if self._closed:
            raise WebSocketDisconnected
        if not self._connected:
            error_msg = "Accept the WebSocket before sending or receiving messages"
            raise RuntimeError(error_msg)

    async def receive(self) -> str | bytes:
        """Receive one text or binary message with a bounded application size.

        Returns
        -------
        str | bytes
            The next complete application message.

        Raises
        ------
        WebSocketDisconnected
            If the peer disconnects or sends an oversized message.
        RuntimeError
            If not accepted or another receive is in progress.
        """
        self._requireOpen()
        if self._receive_lock.locked():
            error_msg = "Only one WebSocket receive may run at a time"
            raise RuntimeError(error_msg)
        async with self._receive_lock:
            try:
                data = await self._receiveMessage()
            except _DISCONNECTED as exc:
                self._closed = True
                raise WebSocketDisconnected from exc
            size = len(data.encode("utf-8")) if isinstance(data, str) else len(data)
            if size > self._max_message_size:
                code = (
                    _MESSAGE_TOO_BIG
                    if self._interface is Interface.ASGI else _NORMAL_CLOSE
                )
                await self.close(code=code)
                raise WebSocketDisconnected(_MESSAGE_TOO_BIG, "Message too large")
            return data

    async def _receiveMessage(self) -> str | bytes:
        """Translate one transport event to an application message.

        Returns
        -------
        str | bytes
            Complete text or binary data.

        Raises
        ------
        WebSocketDisconnected
            If a disconnect event arrives.
        RuntimeError
            If the protocol supplies an unexpected event.
        """
        if self._interface is Interface.ASGI:
            event = await self._receive()
            if event["type"] == "websocket.disconnect":
                self._closed = True
                raise WebSocketDisconnected(
                    event.get("code", 1006), event.get("reason", ""),
                )
            if event["type"] == "websocket.receive":
                data = event.get("text")
                if data is None:
                    data = event.get("bytes")
                if isinstance(data, (str, bytes)):
                    return data
        else:
            event = await self._transport.receive()
            if event.kind == 0:
                self._closed = True
                raise WebSocketDisconnected
            if event.kind in {1, 2} and isinstance(event.data, (str, bytes)):
                return event.data
        error_msg = "Unexpected WebSocket receive event"
        raise RuntimeError(error_msg)

    async def send(self, data: str | bytes) -> None:
        """Send one message and await transport backpressure.

        Parameters
        ----------
        data : str | bytes
            Text or binary message.

        Returns
        -------
        None
            Deliver one message without buffering an application queue.

        Raises
        ------
        TypeError
            If data is neither text nor bytes.
        WebSocketDisconnected
            If the peer disconnects.
        RuntimeError
            If the handshake has not been accepted.
        """
        if not isinstance(data, (str, bytes)):
            error_msg = "WebSocket messages must be str or bytes"
            raise TypeError(error_msg)
        async with self._send_lock:
            self._requireOpen()
            try:
                if self._interface is Interface.ASGI:
                    key = "text" if isinstance(data, str) else "bytes"
                    await self._send({"type": "websocket.send", key: data})
                elif isinstance(data, str):
                    await self._transport.send_str(data)
                else:
                    await self._transport.send_bytes(data)
            except _DISCONNECTED as exc:
                self._closed = True
                raise WebSocketDisconnected from exc

    async def sendJson(self, data: object) -> None:
        """Encode a JSON value and send it as text.

        Parameters
        ----------
        data : object
            JSON-serializable payload.

        Returns
        -------
        None
            Await delivery of the encoded message.
        """
        await self.send(msgspec.json.encode(data).decode("utf-8"))

    async def receiveJson(self) -> object:
        """Decode the next text or binary message as JSON.

        Returns
        -------
        object
            Decoded JSON value.

        Raises
        ------
        msgspec.DecodeError
            If the next application message is invalid JSON.
        """
        return msgspec.json.decode(await self.receive())

    async def reject(self, status_code: int = 403) -> None:
        """Reject a handshake before acceptance.

        Parameters
        ----------
        status_code : int, optional
            HTTP rejection status. ASGI uses 403 without the denial extension.

        Returns
        -------
        None
            Reject the pending connection; repeated calls are harmless.

        Raises
        ------
        RuntimeError
            If the connection was already accepted.
        ValueError
            If status_code is not an HTTP error code.
        """
        if not _MIN_HTTP_ERROR <= status_code <= _MAX_HTTP_ERROR:
            error_msg = "WebSocket rejection status must be between 400 and 599"
            raise ValueError(error_msg)
        async with self._send_lock:
            if self._closed:
                return
            if self._connected:
                error_msg = "Cannot reject an accepted WebSocket"
                raise RuntimeError(error_msg)
            try:
                if self._interface is Interface.RSGI:
                    self._protocol.close(status_code)
                else:
                    await self._connectEvent()
                    extensions = self._adapter.getScope().get("extensions", {})
                    if "websocket.http.response" in extensions:
                        await self._send({
                            "type": "websocket.http.response.start",
                            "status": status_code, "headers": [],
                        })
                        await self._send({
                            "type": "websocket.http.response.body", "body": b"",
                        })
                    else:
                        await self._send({"type": "websocket.close", "code": 1008})
            finally:
                self._closed = True

    async def close(self, code: int = _NORMAL_CLOSE, reason: str = "") -> None:
        """Close an accepted connection or reject a pending handshake.

        Parameters
        ----------
        code : int, optional
            ASGI close code; Granian RSGI supports only default closure.
        reason : str, optional
            ASGI close reason; unavailable through Granian RSGI.

        Returns
        -------
        None
            Close the connection; repeated closure is harmless.

        Raises
        ------
        NotImplementedError
            If a custom close code or reason is requested under RSGI.
        ValueError
            If the code or UTF-8 reason is invalid for a close frame.
        """
        if not self._connected:
            await self.reject()
            return
        if self._closed:
            return
        if (
            code not in {1000, 1001, 1002, 1003, 1007, 1008, 1009, 1010, 1011,
                         1012, 1013, 1014}
            and not _MIN_CUSTOM_CLOSE <= code <= _MAX_CUSTOM_CLOSE
        ) or len(reason.encode("utf-8")) > _MAX_CLOSE_REASON:
            error_msg = "Invalid WebSocket close code or reason"
            raise ValueError(error_msg)
        if self._interface is Interface.RSGI and (code != _NORMAL_CLOSE or reason):
            error_msg = "RSGI does not expose WebSocket close frame code or reason"
            raise NotImplementedError(error_msg)
        async with self._send_lock:
            if self._closed:
                return
            try:
                if self._interface is Interface.ASGI:
                    await self._send({
                        "type": "websocket.close", "code": code, "reason": reason,
                    })
                else:
                    self._protocol.close(None)
            finally:
                self._closed = True
