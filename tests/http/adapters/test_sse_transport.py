import asyncio
from collections import deque
from typing import TYPE_CHECKING, Self
from orionis.background.task import BackgroundTask
from orionis.http import EventStreamResponse, ServerSentEvent, StreamingResponse
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

class _Producer:

    __slots__ = (
        "close_error", "closed", "closing", "error", "gate", "history",
        "items", "pulls", "release_close", "started",
    )

    def __init__(self, history: list[str]) -> None:
        """Prepare a controllable, closeable asynchronous event source.

        Parameters
        ----------
        history : list[str]
            Shared record of transport, source, and background activity.

        Returns
        -------
        None
            Initialize the source controls and lifecycle counters.
        """
        self.history = history
        self.items = iter(("first", ServerSentEvent(data="second", id="2")))
        self.pulls = 0
        self.closed = 0
        self.started = asyncio.Event()
        self.closing = asyncio.Event()
        self.gate = None
        self.release_close = None
        self.error = None
        self.close_error = None

    def __aiter__(self) -> Self:
        """Return the same iterator to expose ownership counts.

        Returns
        -------
        Self
            This asynchronous event source.
        """
        return self

    async def __anext__(self) -> ServerSentEvent | str:
        """Suspend or fail before producing the next event.

        Returns
        -------
        ServerSentEvent or str
            The next configured event.

        Raises
        ------
        StopAsyncIteration
            If the source contains no more events.
        """
        self.pulls += 1
        self.started.set()
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration from None

    async def aclose(self) -> None:
        """Record cleanup and optionally suspend or fail during closure.

        Raises
        ------
        Exception
            The configured close failure, if present.
        """
        self.closing.set()
        if self.release_close is not None:
            await self.release_close.wait()
        self.closed += 1
        self.history.append("close")
        if self.close_error is not None:
            raise self.close_error

class _Wire:

    __slots__ = (
        "block_send", "chunks", "disconnected", "error", "error_stage",
        "headers", "history", "messages", "receive_error", "requests",
        "sending", "status", "watcher_closed", "watching",
    )

    def __init__(self) -> None:
        """Expose only the actual ASGI and RSGI HTTP stream operations."""
        self.block_send = None
        self.chunks = []
        self.disconnected = asyncio.Event()
        self.error = ConnectionError("transport failed")
        self.error_stage = None
        self.headers = []
        self.history = []
        self.messages = []
        self.receive_error = None
        self.requests = deque()
        self.sending = asyncio.Event()
        self.status = None
        self.watching = asyncio.Event()
        self.watcher_closed = 0

    def fail(self, stage: str) -> None:
        """Raise a configured transport exception at a known boundary.

        Parameters
        ----------
        stage : str
            Response stage to compare with the configured failure boundary.

        Raises
        ------
        ConnectionError
            If the requested stage matches the configured failure stage.
        """
        if self.error_stage == stage:
            raise self.error

    async def send(self, message: dict) -> None:
        """Record ASGI framing with a controllable transport send boundary.

        Parameters
        ----------
        message : dict
            ASGI response message to record and process.

        Returns
        -------
        None
            Record response metadata or forward the body chunk.
        """
        self.messages.append(message)
        if message["type"] == "http.response.start":
            self.fail("start")
            self.status = message["status"]
            self.headers = [(k.decode(), v.decode()) for k, v in message["headers"]]
        elif message["more_body"]:
            await self.send_bytes(message["body"])
        else:
            self.fail("end")
            self.history.append("end")

    async def receive(self) -> dict:
        """Drain queued HTTP request messages, then wait for disconnect.

        Returns
        -------
        dict
            The next queued request message or disconnect notification.
        """
        if self.requests:
            return self.requests.popleft()
        await self.client_disconnect()
        return {"type": "http.disconnect"}

    async def clientDisconnect(self) -> None:
        """Model Granian's awaitable client disconnect notification.

        Raises
        ------
        BaseException
            A configured receive failure, including cancellation.
        """
        self.watching.set()
        try:
            if self.receive_error is not None:
                raise self.receive_error
            await self.disconnected.wait()
        finally:
            self.watcher_closed += 1

    def responseStream(self, status: int, headers: list[tuple[str, str]]) -> Self:
        """Open the RSGI stream and retain metadata.

        Parameters
        ----------
        status : int
            HTTP response status code.
        headers : list[tuple[str, str]]
            Response headers supplied by the adapter.

        Returns
        -------
        Self
            This transport, ready to send response bytes.
        """
        self.fail("start")
        self.status = status
        self.headers = headers
        return self

    def responseEmpty(self, status: int, headers: list[tuple[str, str]]) -> None:
        """Record an RSGI HEAD response without opening its stream.

        Parameters
        ----------
        status : int
            HTTP response status code.
        headers : list[tuple[str, str]]
            Response headers supplied by the adapter.

        Returns
        -------
        None
            Store the response metadata and record completion.
        """
        self.fail("start")
        self.status = status
        self.headers = headers
        self.history.append("end")

    async def sendBytes(self, chunk: bytes) -> None:
        """Block or fail a send without prefetching the next event.

        Parameters
        ----------
        chunk : bytes
            Encoded response event to send.

        Returns
        -------
        None
            Record the chunk after any configured send gate is released.
        """
        self.sending.set()
        self.fail("body")
        if self.block_send is not None:
            await self.block_send.wait()
        self.chunks.append(chunk)
        self.history.append("send")

    async def background(self) -> None:
        """Record successful delivery's associated background work."""
        self.history.append("background")

    client_disconnect = clientDisconnect
    response_stream = responseStream
    response_empty = responseEmpty
    send_bytes = sendBytes

class TestSSETransport(TestCase):

    async def deliver(
        self, name: str, wire: _Wire, response: EventStreamResponse,
        method: str = "GET",
    ) -> None:
        """Deliver through either real adapter using equivalent metadata.

        Parameters
        ----------
        name : str
            Adapter identifier, either ``"asgi"`` or ``"rsgi"``.
        wire : _Wire
            Transport double used for response operations.
        response : EventStreamResponse
            Response delivered through the selected adapter.
        method : str, optional
            Request method supplied to the transport adapter.

        Returns
        -------
        None
            Complete response delivery through the selected protocol.
        """
        request = ASGITransportAdapter({"method": method, "headers": []})
        if name == "asgi":
            await ASGIResponseAdapter().send(request, response, wire.receive, wire.send)
        else:
            await RSGIResponseAdapter().send(request, response, wire)

    def assertNoTasks(self) -> None:
        """Ensure every temporary SSE task has been joined."""
        self.assertEqual([
            task.get_name() for task in asyncio.all_tasks()
            if task.get_name().startswith("orionis.sse.")
        ], [])

    async def testNormalDeliveryHeadersFramingAndBackground(self) -> None:
        """Send each event and close before background work on both protocols."""
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                source = _Producer(wire.history)
                response = EventStreamResponse(
                    source, status_code=201, background=BackgroundTask(wire.background),
                )
                await self.deliver(name, wire, response)
                self.assertEqual(wire.status, 201)
                self.assertEqual(wire.chunks, [
                    b"data: first\n\n", b"id: 2\ndata: second\n\n",
                ])
                self.assertEqual(dict(wire.headers)["content-type"],
                                 "text/event-stream; charset=utf-8")
                self.assertNotIn("content-length", dict(wire.headers))
                self.assertNotIn("connection", dict(wire.headers))
                self.assertEqual(source.closed, 1)
                self.assertLess(wire.history.index("close"),
                                wire.history.index("background"))
                self.assertEqual(wire.watcher_closed, 1)
                if name == "asgi":
                    self.assertEqual(wire.messages[-1], {
                        "type": "http.response.body", "body": b"", "more_body": False,
                    })
                self.assertNoTasks()

    async def testDisconnectStopsIdleProducerAndSkipsBackground(self) -> None:
        """Detect disconnect while the next event is indefinitely suspended."""
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                source = _Producer(wire.history)
                source.gate = asyncio.Event()
                response = EventStreamResponse(
                    source, background=BackgroundTask(wire.background),
                )
                task = asyncio.create_task(self.deliver(name, wire, response))
                async with asyncio.timeout(2):
                    await source.started.wait()
                    wire.disconnected.set()
                    await task
                self.assertEqual(source.pulls, 1)
                self.assertEqual(source.closed, 1)
                self.assertEqual(wire.chunks, [])
                self.assertNotIn("background", wire.history)
                self.assertNotIn("end", wire.history)
                self.assertNoTasks()

    async def testTransportBackpressureAndDisconnectDuringSend(self) -> None:
        """Stop a blocked send without requesting another producer item."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            wire.block_send = asyncio.Event()
            source = _Producer(wire.history)
            response = EventStreamResponse(
                source, background=BackgroundTask(wire.background),
            )
            task = asyncio.create_task(self.deliver(name, wire, response))
            async with asyncio.timeout(2):
                await wire.sending.wait()
                self.assertEqual(source.pulls, 1)
                wire.disconnected.set()
                await task
            self.assertEqual(source.pulls, 1)
            self.assertEqual(source.closed, 1)
            self.assertNotIn("background", wire.history)
            self.assertNoTasks()

    async def testFailuresPropagateAndAlwaysClose(self) -> None:
        """Preserve producer, send, receive and close errors without background."""
        for name in ("asgi", "rsgi"):
            stages = ("start", "body", "producer", "close", "receive")
            if name == "asgi":
                stages += ("end",)
            for stage in stages:
                with self.subTest(protocol=name, stage=stage):
                    wire = _Wire()
                    source = _Producer(wire.history)
                    error = RuntimeError(stage)
                    wire.error = error
                    wire.error_stage = stage
                    if stage == "producer":
                        source.error = error
                    elif stage == "close":
                        source.close_error = error
                    elif stage == "receive":
                        source.gate = asyncio.Event()
                        wire.receive_error = error
                    response = EventStreamResponse(
                        source, background=BackgroundTask(wire.background),
                    )
                    with self.assertRaises(RuntimeError) as caught:
                        await self.deliver(name, wire, response)
                    self.assertIs(caught.exception, error)
                    self.assertEqual(source.closed, 1)
                    self.assertNotIn("background", wire.history)
                    self.assertNoTasks()

    async def testCancellationPropagatesAfterCleanup(self) -> None:
        """Cancel a request while its producer waits and join both tasks."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            source = _Producer(wire.history)
            source.gate = asyncio.Event()
            response = EventStreamResponse(
                source, background=BackgroundTask(wire.background),
            )
            task = asyncio.create_task(self.deliver(name, wire, response))
            async with asyncio.timeout(2):
                await source.started.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertEqual(source.closed, 1)
            self.assertEqual(wire.watcher_closed, 1)
            self.assertNotIn("background", wire.history)
            self.assertNoTasks()

    async def testRepeatedCancellationWaitsForAsyncCleanup(self) -> None:
        """Do not orphan cleanup if the request is cancelled more than once."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            source = _Producer(wire.history)
            source.gate = asyncio.Event()
            source.release_close = asyncio.Event()
            response = EventStreamResponse(
                source, background=BackgroundTask(wire.background),
            )
            task = asyncio.create_task(self.deliver(name, wire, response))
            async with asyncio.timeout(2):
                await source.started.wait()
                task.cancel()
                await source.closing.wait()
                task.cancel()
                self.assertFalse(task.done())
                source.release_close.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertEqual(source.closed, 1)
            self.assertNotIn("background", wire.history)
            self.assertNoTasks()

    async def testDisconnectDuringNormalCleanupWaitsForClose(self) -> None:
        """Finish an asynchronous close interrupted by the disconnect watcher."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            source = _Producer(wire.history)
            source.release_close = asyncio.Event()
            response = EventStreamResponse(
                source, background=BackgroundTask(wire.background),
            )
            task = asyncio.create_task(self.deliver(name, wire, response))
            async with asyncio.timeout(2):
                await source.closing.wait()
                wire.disconnected.set()
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                self.assertFalse(task.done())
                source.release_close.set()
                await task
            self.assertEqual(source.closed, 1)
            self.assertNotIn("background", wire.history)
            self.assertNoTasks()

    async def testHeadNeverStartsAsyncGenerator(self) -> None:
        """Send headers and an empty body without entering a generator."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            started = []

            async def events(record: list = started) -> AsyncIterator[str]:
                """Record entering a generator that HEAD must never start.

                Parameters
                ----------
                record : list
                    Collection receiving a marker if iteration begins.

                Yields
                ------
                str
                    A forbidden event, if the generator is entered.
                """
                record.append(True)
                yield "forbidden"

            response = EventStreamResponse(
                events(), background=BackgroundTask(wire.background),
            )
            await self.deliver(name, wire, response, "HEAD")
            self.assertEqual(started, [])
            self.assertEqual(wire.chunks, [])
            self.assertEqual(wire.history, ["end", "background"])
            self.assertNotIn("content-length", dict(wire.headers))
            self.assertFalse(wire.watching.is_set())
            self.assertNoTasks()

    async def testDisconnectDoesNotHideCleanupFailure(self) -> None:
        """Propagate a real close failure even if disconnect cancels cleanup."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            source = _Producer(wire.history)
            source.release_close = asyncio.Event()
            source.close_error = RuntimeError("cleanup failed after disconnect")
            response = EventStreamResponse(
                source, background=BackgroundTask(wire.background),
            )
            task = asyncio.create_task(self.deliver(name, wire, response))
            async with asyncio.timeout(2):
                await source.closing.wait()
                wire.disconnected.set()
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                source.release_close.set()
                with self.assertRaises(RuntimeError) as caught:
                    await task
            self.assertIs(caught.exception, source.close_error)
            self.assertEqual(source.closed, 1)
            self.assertNotIn("background", wire.history)
            self.assertNoTasks()

    async def testHeadClosesUnstartedSourceOnSuccessOrFailure(self) -> None:
        """Close owned custom sources on HEAD even if headers fail to send."""
        for name in ("asgi", "rsgi"):
            for stage in (None, "start"):
                wire = _Wire()
                wire.error_stage = stage
                source = _Producer(wire.history)
                response = EventStreamResponse(source)
                if stage is None:
                    await self.deliver(name, wire, response, "HEAD")
                else:
                    with self.assertRaises(ConnectionError):
                        await self.deliver(name, wire, response, "HEAD")
                self.assertEqual(source.pulls, 0)
                self.assertEqual(source.closed, 1)

    async def testAsgiDrainsUnreadBodyBeforeDisconnect(self) -> None:
        """Treat HTTP request chunks as input, never as disconnect messages."""
        wire = _Wire()
        wire.requests.extend((
            {"type": "http.request", "body": b"a", "more_body": True},
            {"type": "http.request", "body": b"b", "more_body": False},
        ))
        source = _Producer(wire.history)
        source.gate = asyncio.Event()
        task = asyncio.create_task(
            self.deliver("asgi", wire, EventStreamResponse(source)),
        )
        async with asyncio.timeout(2):
            await wire.watching.wait()
            self.assertFalse(task.done())
            self.assertEqual(source.closed, 0)
            wire.disconnected.set()
            await task
        self.assertEqual(source.closed, 1)
        self.assertNoTasks()

    async def testOrdinaryStreamsDoNotObserveDisconnect(self) -> None:
        """Keep normal streams on their existing transport path."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            await self.deliver(name, wire, StreamingResponse([b"ordinary"]))
            self.assertFalse(wire.watching.is_set())
            self.assertEqual(wire.chunks, [b"ordinary"])
            self.assertNoTasks()

    async def testOrdinaryStreamHeaderFailureClosesItsIterator(self) -> None:
        """Keep ownership deterministic when opening a normal stream fails."""
        for name in ("asgi", "rsgi"):
            wire = _Wire()
            wire.error_stage = "start"
            source = _Producer(wire.history)
            source.items = iter((b"ordinary",))
            response = StreamingResponse(
                source, background=BackgroundTask(wire.background),
            )
            with self.assertRaises(ConnectionError):
                await self.deliver(name, wire, response)
            self.assertEqual(source.pulls, 0)
            self.assertEqual(source.closed, 1)
            self.assertFalse(wire.watching.is_set())
            self.assertNotIn("background", wire.history)

    async def testHeaderSerializationFailureClosesUnstartedSource(self) -> None:
        """Close owned SSE sources if header serialization fails before sending."""
        for name in ("asgi", "rsgi"):
            for method in ("GET", "HEAD"):
                with self.subTest(protocol=name, method=method):
                    wire = _Wire()
                    source = _Producer(wire.history)
                    response = EventStreamResponse(
                        source, headers={"x-invalid": object()},
                        background=BackgroundTask(wire.background),
                    )
                    with self.assertRaises(TypeError):
                        await self.deliver(name, wire, response, method)
                    self.assertEqual(source.pulls, 0)
                    self.assertEqual(source.closed, 1)
                    self.assertEqual(wire.chunks, [])
                    self.assertFalse(wire.watching.is_set())
                    self.assertNotIn("background", wire.history)
                    self.assertNoTasks()

    async def testAsgiHeaderEncodingFailureClosesUnstartedSource(self) -> None:
        """Release the event source when a header cannot be encoded as Latin-1."""
        wire = _Wire()
        source = _Producer(wire.history)
        response = EventStreamResponse(
            source, headers={"x-invalid": "\u4e16\u754c"},
            background=BackgroundTask(wire.background),
        )
        with self.assertRaises(UnicodeEncodeError):
            await self.deliver("asgi", wire, response)
        self.assertEqual(source.pulls, 0)
        self.assertEqual(source.closed, 1)
        self.assertFalse(wire.watching.is_set())
        self.assertNotIn("background", wire.history)
        self.assertNoTasks()
