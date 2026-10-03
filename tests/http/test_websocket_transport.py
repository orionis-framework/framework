import asyncio
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from granian._granian import RSGIProtocolClosed, RSGIProtocolError
from orionis.http import (
    WebSocketDisconnected, WebSocketMessage, WebSocketMessageType, WebSocketState,
)
from orionis.test import TestCase
from tests.http.test_websocket import _ASGIPeer, _RSGIPeer

class _ControlledASGIPeer(_ASGIPeer):
    """Expose deterministic barriers around writes and injected server errors."""

    __slots__ = ("active", "entered", "failure", "peak", "release", "writes")

    def __init__(self) -> None:
        """
        Prepare write barriers and counters.

        Returns
        -------
        None
            Initialize deterministic write control.
        """
        super().__init__()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.active = 0
        self.peak = 0
        self.writes = 0
        self.failure: BaseException | None = None

    async def send(self, event: dict) -> None:
        """
        Pause data writes while accepting and closing immediately.

        Parameters
        ----------
        event : dict
            ASGI output event.

        Returns
        -------
        None
            Record the event after the controlled barrier.
        """
        if event["type"] != "websocket.send":
            await super().send(event)
            return
        self.active += 1
        self.writes += 1
        self.peak = max(self.peak, self.active)
        self.entered.set()
        try:
            await self.release.wait()
            if self.failure is not None:
                raise self.failure
            await super().send(event)
        finally:
            self.active -= 1

class _FailingRSGIPeer(_RSGIPeer):
    """Inject Granian errors and controlled binary writes."""

    __slots__ = ("entered", "failure", "release")

    def __init__(self) -> None:
        """
        Initialize optional transport failures and a send barrier.

        Returns
        -------
        None
            Prepare deterministic server behavior.
        """
        super().__init__()
        self.failure: BaseException | None = None
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def receive(self) -> object:
        """
        Raise the configured error or consume the next peer event.

        Returns
        -------
        object
            Queued Granian message when no failure is configured.
        """
        if self.failure is not None:
            raise self.failure
        return await super().receive()

    async def sendBytes(self, data: bytes) -> None:
        """
        Pause and then delegate Granian's exact binary sending API.

        Parameters
        ----------
        data : bytes
            Binary payload.

        Returns
        -------
        None
            Finish the controlled write.
        """
        self.entered.set()
        await self.release.wait()
        if self.failure is not None:
            raise self.failure
        await super().send_bytes(data)

    send_bytes = sendBytes

class TestWebSocketTransportContract(TestCase):
    """Validate public state, cancellation, normalized messages and real APIs."""

    def testMessageIsImmutableAndRetainsPayloadIdentity(self) -> None:
        """
        Keep immutable records and avoid copying binary payloads.

        Returns
        -------
        None
            Verify message ergonomics and payload identity.
        """
        payload = b"unchanged binary payload"
        message = WebSocketMessage(type=WebSocketMessageType.BYTES, data=payload)
        self.assertTrue(message.isBytes())
        self.assertFalse(message.isText())
        self.assertFalse(message.isDisconnect())
        self.assertIs(message.bytes, payload)
        with self.assertRaises(FrozenInstanceError):
            field_name = "data"
            setattr(message, field_name, b"changed")
        with self.assertRaises(TypeError):
            _ = message.text

    async def testStateMachineAndDuplicateCloseAcrossAdapters(self) -> None:
        """
        Require acceptance and prevent terminal operations from reviving peers.

        Returns
        -------
        None
            Verify explicit state transitions and one close operation.
        """
        for peer in (_ASGIPeer(), _RSGIPeer()):
            socket = peer.socket()
            self.assertIs(socket.connectionState, WebSocketState.CONNECTING)
            await socket.accept()
            self.assertIs(socket.connectionState, WebSocketState.CONNECTED)
            await asyncio.gather(socket.close(), socket.close())
            self.assertIs(socket.connectionState, WebSocketState.CLOSED)
            with self.assertRaises(WebSocketDisconnected):
                await socket.receive()
            with self.assertRaises(WebSocketDisconnected):
                await socket.sendText("late")
            with self.assertRaises(RuntimeError):
                await socket.accept()
            if isinstance(peer, _ASGIPeer):
                self.assertEqual(len(peer.sent), 2)
            else:
                self.assertEqual(peer.statuses, [None])

    async def testAsgiAcceptHeadersAndSubprotocolAreVersionAware(self) -> None:
        """
        Negotiate only offered protocols and version-supported headers.

        Returns
        -------
        None
            Verify supported handshake fields and default ASGI 2.0 behavior.
        """
        peer = _ASGIPeer()
        peer.scope["subprotocols"] = ["orionis.json.v1"]
        socket = peer.socket()
        await socket.accept(
            subprotocol="orionis.json.v1", headers={"X-Handshake": "ready"},
        )
        self.assertEqual(peer.sent, [{
            "type": "websocket.accept", "subprotocol": "orionis.json.v1",
            "headers": [(b"x-handshake", b"ready")],
        }])
        older = _ASGIPeer()
        older.scope.pop("asgi")
        socket = older.socket()
        with self.assertRaises(NotImplementedError):
            await socket.accept(headers={"X-Test": "unsupported"})
        self.assertEqual(older.sent, [])
        self.assertEqual(older.events.qsize(), 1)
        await socket.accept()
        await socket.close(reason="local detail")
        self.assertNotIn("reason", older.sent[-1])

    async def testInvalidHandshakeOptionsLeaveHandshakePending(self) -> None:
        """
        Reject invalid or forbidden headers before consuming server events.

        Returns
        -------
        None
            Verify validation has no transport side effects.
        """
        for headers in (
            {"Sec-WebSocket-Protocol": "unsafe"}, {":status": "101"},
            {"X-Test": "bad\r\nvalue"}, {"bad name": "value"},
        ):
            peer = _ASGIPeer()
            with self.assertRaises(ValueError):
                await peer.socket().accept(headers=headers)
            self.assertEqual(peer.events.qsize(), 1)
            self.assertEqual(peer.sent, [])
        peer = _ASGIPeer()
        with self.assertRaises(ValueError):
            await peer.socket().accept(subprotocol="not-offered")
        self.assertEqual(peer.sent, [])

    async def testPeerDisconnectDuringHandshakeRetainsDetails(self) -> None:
        """
        Preserve close metadata even before acceptance.

        Returns
        -------
        None
            Verify no accept frame is emitted after peer disconnection.
        """
        peer = _ASGIPeer()
        peer.events.get_nowait()
        peer.events.put_nowait({
            "type": "websocket.disconnect", "code": 1001, "reason": "departed",
        })
        socket = peer.socket()
        with self.assertRaises(WebSocketDisconnected) as caught:
            await socket.accept()
        self.assertEqual((caught.exception.code, caught.exception.reason), (
            1001, "departed",
        ))
        self.assertTrue(socket.closed)
        self.assertEqual(peer.sent, [])

    async def testAsgiRejectsInvalidReceiveFrames(self) -> None:
        """
        Reject ambiguous, empty and incorrectly typed server messages.

        Returns
        -------
        None
            Verify exact ASGI text/binary event discrimination.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        for payload in (
            {"text": "both", "bytes": b"both"}, {},
            {"text": None, "bytes": None}, {"bytes": "not bytes"},
        ):
            peer.events.put_nowait({"type": "websocket.receive", **payload})
            with self.assertRaises(RuntimeError):
                await socket.receive()

    async def testTypedReceivesAndIteration(self) -> None:
        """
        Decode typed data and stop iteration on the terminal peer event.

        Returns
        -------
        None
            Verify helpers, Unicode, binary JSON and iterator termination.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        for payload in (
            {"text": "Hola 🌎"}, {"bytes": b"\x00\xff"},
            {"bytes": b'{"binary":true}'}, {"text": "item"},
        ):
            peer.events.put_nowait({"type": "websocket.receive", **payload})
        peer.events.put_nowait({"type": "websocket.disconnect", "code": 1000})
        self.assertEqual(await socket.receiveText(), "Hola 🌎")
        self.assertEqual(await socket.receiveBytes(), b"\x00\xff")
        self.assertEqual(await socket.receiveJson(), {"binary": True})
        self.assertEqual([message.text async for message in socket], ["item"])
        self.assertTrue(socket.closed)

    async def testTypedReceivesRejectWrongKindsAndDisconnects(self) -> None:
        """
        Avoid implicit coercion between text and binary payloads.

        Returns
        -------
        None
            Verify type errors consume one message and closure remains terminal.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        peer.events.put_nowait({"type": "websocket.receive", "bytes": b"binary"})
        with self.assertRaises(TypeError):
            await socket.receiveText()
        peer.events.put_nowait({"type": "websocket.receive", "text": "text"})
        with self.assertRaises(TypeError):
            await socket.receiveBytes()
        peer.events.put_nowait({"type": "websocket.disconnect", "code": 1001})
        with self.assertRaises(WebSocketDisconnected):
            await socket.receiveJson()

    async def testConcurrentSendsAwaitOneSerializedNetworkWrite(self) -> None:
        """
        Preserve server backpressure without parallel transport writes.

        Returns
        -------
        None
            Verify one writer, ordering and pending callers under backpressure.
        """
        peer = _ControlledASGIPeer()
        socket = peer.socket()
        await socket.accept()
        first = asyncio.create_task(socket.sendText("first"))
        await peer.entered.wait()
        second = asyncio.create_task(socket.sendBytes(b"second"))
        await asyncio.sleep(0)
        self.assertFalse(first.done())
        self.assertFalse(second.done())
        self.assertEqual(peer.writes, 1)
        peer.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(peer.peak, 1)
        self.assertEqual(peer.sent[1:], [
            {"type": "websocket.send", "text": "first"},
            {"type": "websocket.send", "bytes": b"second"},
        ])

    async def testCancelledWriteRequiresClosureAndReleasesSendLock(self) -> None:
        """
        Prevent further messages after an interrupted network write.

        Returns
        -------
        None
            Verify cancellation propagation and deadlock-free cleanup.
        """
        for peer in (_ControlledASGIPeer(), _FailingRSGIPeer()):
            socket = peer.socket()
            await socket.accept()
            task = asyncio.create_task(socket.sendBytes(b"interrupted"))
            await peer.entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertIs(socket.connectionState, WebSocketState.CLOSING)
            with self.assertRaises(WebSocketDisconnected):
                await socket.sendText("unsafe retry")
            await asyncio.wait_for(socket.close(), timeout=1)
            self.assertTrue(socket.closed)

    async def testCancelledWaitingWriterDoesNotCancelActiveWrite(self) -> None:
        """
        Keep cancellation before lock acquisition local to the waiting caller.

        Returns
        -------
        None
            Verify the active send and connection remain usable.
        """
        peer = _ControlledASGIPeer()
        socket = peer.socket()
        await socket.accept()
        first = asyncio.create_task(socket.sendText("first"))
        await peer.entered.wait()
        waiting = asyncio.create_task(socket.sendText("cancelled waiter"))
        await asyncio.sleep(0)
        waiting.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiting
        self.assertIs(socket.connectionState, WebSocketState.CONNECTED)
        peer.release.set()
        await first
        self.assertEqual(peer.writes, 1)

    async def testCancelledReaderReleasesConsumerAcrossAdapters(self) -> None:
        """
        Allow a new consumer after cancellation of an idle receive.

        Returns
        -------
        None
            Verify cancellation propagation without lock or state leakage.
        """
        for peer in (_ASGIPeer(), _RSGIPeer()):
            socket = peer.socket()
            await socket.accept()
            task = asyncio.create_task(socket.receive())
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertIs(socket.connectionState, WebSocketState.CONNECTED)
            event = (
                {"type": "websocket.receive", "text": "resumed"}
                if isinstance(peer, _ASGIPeer)
                else SimpleNamespace(kind=2, data="resumed")
            )
            peer.events.put_nowait(event)
            self.assertEqual(await socket.receiveText(), "resumed")

    async def testServerErrorIsNotHiddenAndWriteLockIsReleased(self) -> None:
        """
        Propagate server failures without converting them to peer disconnects.

        Returns
        -------
        None
            Verify original exception identity and lock release.
        """
        peer = _ControlledASGIPeer()
        peer.release.set()
        peer.failure = RuntimeError("ASGI server failure")
        socket = peer.socket()
        await socket.accept()
        with self.assertRaises(RuntimeError) as caught:
            await socket.sendText("fails")
        self.assertIs(caught.exception, peer.failure)
        peer.failure = None
        await asyncio.wait_for(socket.sendText("works"), timeout=1)
        self.assertEqual(peer.sent[-1]["text"], "works")

    async def testRsgiMessageKindsAndUnsupportedHandshakeOptions(self) -> None:
        """
        Normalize actual Granian kinds and reject unavailable features.

        Returns
        -------
        None
            Verify binary/text discrimination and terminal kind zero.
        """
        peer = _RSGIPeer()
        socket = peer.socket()
        with self.assertRaises(NotImplementedError):
            await socket.accept(subprotocol="unsupported")
        with self.assertRaises(NotImplementedError):
            await socket.accept(headers={"X-Test": "unsupported"})
        self.assertEqual(peer.accepts, 0)
        await socket.accept()
        for kind, payload in ((1, "bad"), (2, b"bad"), (3, "bad")):
            peer.events.put_nowait(SimpleNamespace(kind=kind, data=payload))
            with self.assertRaises(RuntimeError):
                await socket.receive()
        peer.events.put_nowait(SimpleNamespace(kind=0, data=None))
        message = await socket.receive()
        self.assertTrue(message.isDisconnect())
        self.assertEqual(message.code, 1006)
        self.assertIsNone(message.reason)
        self.assertTrue(socket.closed)

    async def testRsgiTransportErrorsDistinguishClosureAndProtocolFailure(self) -> None:
        """
        Translate actual closed exceptions and preserve server protocol errors.

        Returns
        -------
        None
            Verify normalized disconnect causes and visible server failures.
        """
        peer = _FailingRSGIPeer()
        socket = peer.socket()
        await socket.accept()
        peer.failure = RSGIProtocolError("protocol failure")
        with self.assertRaises(RSGIProtocolError) as caught:
            await socket.receive()
        self.assertIs(caught.exception, peer.failure)
        peer.failure = RSGIProtocolClosed("closed")
        with self.assertRaises(WebSocketDisconnected) as caught:
            await socket.receive()
        self.assertIs(caught.exception.__cause__, peer.failure)
        self.assertTrue(socket.closed)

    async def testReaderSuspendedBeforeCloseCannotDeliverLateData(self) -> None:
        """
        Prevent a previously waiting receive from reviving a closed socket.

        Returns
        -------
        None
            Verify closure remains terminal under read/write races.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        task = asyncio.create_task(socket.receive())
        await asyncio.sleep(0)
        await socket.close()
        peer.events.put_nowait({"type": "websocket.receive", "text": "late"})
        with self.assertRaises(WebSocketDisconnected):
            await task

    async def testConcurrentAcceptanceEmitsOnlyOneHandshake(self) -> None:
        """
        Serialize acceptance and reject the second caller explicitly.

        Returns
        -------
        None
            Verify no duplicate handshake frame is emitted.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        results = await asyncio.gather(
            socket.accept(), socket.accept(), return_exceptions=True,
        )
        self.assertIsNone(results[0])
        self.assertIsInstance(results[1], RuntimeError)
        self.assertEqual(peer.sent, [{"type": "websocket.accept"}])
