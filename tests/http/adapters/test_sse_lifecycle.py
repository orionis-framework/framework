import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING
from orionis.background.task import BackgroundTask
from orionis.http import EventStreamResponse
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.adapters.response.streams import send_until_disconnect
from orionis.test import TestCase
from tests.http.adapters.test_sse_transport import _Producer, _Wire

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


async def deliver(name: str, wire: _Wire, response: EventStreamResponse) -> None:
    """Exercise each response adapter with equivalent request metadata.

    Parameters
    ----------
    name : str
        Adapter identifier, either ``"asgi"`` or ``"rsgi"``.
    wire : _Wire
        Transport double used for send and disconnect operations.
    response : EventStreamResponse
        Event stream delivered through the selected adapter.

    Returns
    -------
    None
        Complete response delivery through the selected protocol.
    """
    request = ASGITransportAdapter({"method": "GET", "headers": []})
    if name == "asgi":
        await ASGIResponseAdapter().send(request, response, wire.receive, wire.send)
    else:
        await RSGIResponseAdapter().send(request, response, wire)


class _GeneratorState:
    """Expose an actual async generator with interruptible asynchronous cleanup."""

    __slots__ = (
        "cleanup_done", "cleanup_interrupted", "cleanup_started", "idle",
        "release_cleanup", "waiting",
    )

    def __init__(self) -> None:
        """Create controls that distinguish producing from finalization.

        Returns
        -------
        None
            Initialize producer and cleanup synchronization events.
        """
        self.idle = asyncio.Event()
        self.waiting = asyncio.Event()
        self.cleanup_started = asyncio.Event()
        self.cleanup_done = asyncio.Event()
        self.cleanup_interrupted = asyncio.Event()
        self.release_cleanup = asyncio.Event()

    async def events(self, *, hold: bool) -> AsyncIterator[str]:
        """Yield once, then finalize either naturally or after cancellation.

        Parameters
        ----------
        hold : bool
            Whether to wait after yielding until the test releases the producer.

        Yields
        ------
        str
            The initial event before the producer pauses.
        """
        try:
            yield "first"
            if hold:
                self.waiting.set()
                await self.idle.wait()
        finally:
            self.cleanup_started.set()
            try:
                await self.release_cleanup.wait()
            except asyncio.CancelledError:
                self.cleanup_interrupted.set()
                raise
            self.cleanup_done.set()

    async def protectedEvents(self) -> AsyncIterator[str]:
        """Protect and join application cleanup reached during normal exhaustion.

        Yields
        ------
        str
            The initial event before protected cleanup begins.
        """
        try:
            yield "first"
        finally:
            cleanup = asyncio.create_task(self.finishCleanup())
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                await cleanup
                raise

    async def finishCleanup(self) -> None:
        """Release an application's resource after its explicit finalization gate.

        Returns
        -------
        None
            Signal completion after the test releases the cleanup gate.
        """
        self.cleanup_started.set()
        await self.release_cleanup.wait()
        self.cleanup_done.set()


class _BlockingStartWire(_Wire):
    """Suspend ASGI response.start before the source iterator is entered."""

    __slots__ = ("release_start", "starting")

    def __init__(self) -> None:
        """Initialize the ordinary wire plus a header send boundary.

        Returns
        -------
        None
            Initialize the response-start synchronization events.
        """
        super().__init__()
        self.starting = asyncio.Event()
        self.release_start = asyncio.Event()

    async def send(self, message: dict) -> None:
        """Wait during the response start message, then use ordinary framing.

        Parameters
        ----------
        message : dict
            ASGI response message passed to the transport.

        Returns
        -------
        None
            Forward the message after the response-start gate is released.
        """
        if message["type"] == "http.response.start":
            self.starting.set()
            await self.release_start.wait()
        await super().send(message)


class TestSSELifecycle(TestCase):
    """Cover cancellation races at generator and transport lifetime boundaries."""

    def assertNoTasks(self) -> None:
        """Ensure every temporary SSE sender and watcher has been joined.

        Returns
        -------
        None
            Assert that no named SSE tasks remain active.
        """
        self.assertEqual([
            task.get_name() for task in asyncio.all_tasks()
            if task.get_name().startswith("orionis.sse.")
        ], [])

    async def testDisconnectWinsWhenBothTasksFinishInTheSameTurn(self) -> None:
        """Do not report successful delivery after an earlier disconnect.

        Returns
        -------
        None
            Verify disconnect ordering wins when both tasks finish together.
        """
        release = asyncio.Event()
        order = []

        async def sending() -> None:
            """Complete only after the disconnect has been observed.

            Returns
            -------
            None
                Record send completion after the disconnect signal.
            """
            await release.wait()
            order.append("send")

        async def disconnected() -> None:
            """Record disconnection and let the producer finish in this turn.

            Returns
            -------
            None
                Signal the sender after recording disconnection.
            """
            order.append("disconnect")
            release.set()

        completed = await send_until_disconnect(sending(), disconnected())
        self.assertEqual(order, ["disconnect", "send"])
        self.assertFalse(completed)
        self.assertNoTasks()

    async def testDeliveryWinsWhenDisconnectFollowsCompletion(self) -> None:
        """Keep successful delivery when disconnect follows the final body.

        Returns
        -------
        None
            Verify completed delivery wins over a later disconnect.
        """
        release = asyncio.Event()
        order = []

        async def sending() -> None:
            """Complete delivery before the disconnect becomes observable.

            Returns
            -------
            None
                Record completion and release the disconnect watcher.
            """
            order.append("send")
            release.set()

        async def disconnected() -> None:
            """Observe disconnect after the response has already completed.

            Returns
            -------
            None
                Record disconnection after the sender releases the gate.
            """
            await release.wait()
            order.append("disconnect")

        completed = await send_until_disconnect(sending(), disconnected())
        self.assertEqual(order, ["send", "disconnect"])
        self.assertTrue(completed)
        self.assertNoTasks()

    async def testDisconnectJoinsSuspendedAsyncGeneratorFinally(self) -> None:
        """Keep finalization owned after disconnect interrupts an idle producer.

        Returns
        -------
        None
            Verify disconnect waits for the producer's asynchronous finalizer.
        """
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                state = _GeneratorState()
                response = EventStreamResponse(
                    state.events(hold=True), background=BackgroundTask(wire.background),
                )
                task = asyncio.create_task(deliver(name, wire, response))
                try:
                    async with asyncio.timeout(2):
                        await state.waiting.wait()
                        wire.disconnected.set()
                        await state.cleanup_started.wait()
                        self.assertFalse(task.done())
                        self.assertFalse(state.cleanup_done.is_set())
                        state.release_cleanup.set()
                        await task
                finally:
                    state.release_cleanup.set()
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                self.assertTrue(state.cleanup_done.is_set())
                self.assertFalse(state.cleanup_interrupted.is_set())
                self.assertNotIn("background", wire.history)
                self.assertNoTasks()

    async def testRepeatedCancellationJoinsAsyncGeneratorFinally(self) -> None:
        """Propagate request cancellation after a real generator finishes cleanup.

        Returns
        -------
        None
            Verify repeated cancellation does not interrupt generator cleanup.
        """
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                state = _GeneratorState()
                response = EventStreamResponse(
                    state.events(hold=True), background=BackgroundTask(wire.background),
                )
                task = asyncio.create_task(deliver(name, wire, response))
                try:
                    async with asyncio.timeout(2):
                        await state.waiting.wait()
                        task.cancel()
                        await state.cleanup_started.wait()
                        task.cancel()
                        await asyncio.sleep(0)
                        self.assertFalse(task.done())
                        state.release_cleanup.set()
                        with self.assertRaises(asyncio.CancelledError):
                            await task
                finally:
                    state.release_cleanup.set()
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                self.assertTrue(state.cleanup_done.is_set())
                self.assertFalse(state.cleanup_interrupted.is_set())
                self.assertNotIn("background", wire.history)
                self.assertNoTasks()

    async def testProducerCanShieldNaturalFinalizationFromDisconnect(self) -> None:
        """Join application-protected cleanup already entered during exhaustion.

        Returns
        -------
        None
            Verify disconnect joins cleanup protected by the producer.
        """
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                state = _GeneratorState()
                response = EventStreamResponse(
                    state.protectedEvents(),
                    background=BackgroundTask(wire.background),
                )
                task = asyncio.create_task(deliver(name, wire, response))
                try:
                    async with asyncio.timeout(2):
                        await state.cleanup_started.wait()
                        wire.disconnected.set()
                        for _ in range(4):
                            await asyncio.sleep(0)
                        state.release_cleanup.set()
                        await task
                finally:
                    state.release_cleanup.set()
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                self.assertTrue(state.cleanup_done.is_set())
                self.assertFalse(state.cleanup_interrupted.is_set())
                self.assertNotIn("background", wire.history)
                self.assertNoTasks()

    async def testProducerCancellationPropagatesAndSkipsBackground(self) -> None:
        """Treat a producer's own CancelledError as request cancellation.

        Returns
        -------
        None
            Verify producer cancellation propagates and background work is skipped.
        """
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                source = _Producer(wire.history)
                source.error = asyncio.CancelledError("producer cancelled")
                response = EventStreamResponse(
                    source, background=BackgroundTask(wire.background),
                )
                with self.assertRaises(asyncio.CancelledError):
                    await deliver(name, wire, response)
                self.assertEqual(source.closed, 1)
                self.assertNotIn("background", wire.history)
                self.assertNoTasks()

    async def testWatcherCancellationPropagatesAndClosesIdleProducer(self) -> None:
        """Do not classify spontaneous watcher cancellation as normal disconnect.

        Returns
        -------
        None
            Verify watcher cancellation propagates after producer cleanup.
        """
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                wire.receive_error = asyncio.CancelledError("watcher cancelled")
                source = _Producer(wire.history)
                source.gate = asyncio.Event()
                response = EventStreamResponse(
                    source, background=BackgroundTask(wire.background),
                )
                with self.assertRaises(asyncio.CancelledError):
                    await deliver(name, wire, response)
                self.assertEqual(source.closed, 1)
                self.assertNotIn("background", wire.history)
                self.assertNoTasks()

    async def testWatcherCancellationAtCompletionStillSkipsBackground(self) -> None:
        """Preserve spontaneous watcher cancellation even if delivery just ended.

        Returns
        -------
        None
            Verify watcher cancellation suppresses background work at completion.
        """
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                wire.receive_error = asyncio.CancelledError("watcher cancelled")
                response = EventStreamResponse(
                    ("first",), background=BackgroundTask(wire.background),
                )
                with self.assertRaises(asyncio.CancelledError):
                    await deliver(name, wire, response)
                self.assertNotIn("background", wire.history)
                self.assertNoTasks()

    async def testSimultaneousProducerAndWatcherErrorsArePreserved(self) -> None:
        """Retain both real failures if notification fails in the same turn.

        Returns
        -------
        None
            Verify simultaneous producer and watcher errors are both preserved.
        """
        for name in ("asgi", "rsgi"):
            with self.subTest(protocol=name):
                wire = _Wire()
                wire.receive_error = LookupError("watcher failed")
                source = _Producer(wire.history)
                source.error = RuntimeError("producer failed")
                response = EventStreamResponse(
                    source, background=BackgroundTask(wire.background),
                )
                with self.assertRaises(BaseExceptionGroup) as caught:
                    await deliver(name, wire, response)
                self.assertIn(source.error, caught.exception.exceptions)
                self.assertIn(wire.receive_error, caught.exception.exceptions)
                self.assertEqual(source.closed, 1)
                self.assertNotIn("background", wire.history)
                self.assertNoTasks()

    async def testInvalidAsgiReceiveMessageClosesProducerAndRaises(self) -> None:
        """Reject unrelated ASGI message types without consuming more events.

        Returns
        -------
        None
            Verify invalid input raises and closes the producer without sending.
        """
        wire = _Wire()
        wire.requests.append({"type": "websocket.disconnect", "code": 1000})
        source = _Producer(wire.history)
        source.gate = asyncio.Event()
        response = EventStreamResponse(
            source, background=BackgroundTask(wire.background),
        )
        with self.assertRaisesRegex(RuntimeError, "Unexpected ASGI message"):
            await deliver("asgi", wire, response)
        self.assertEqual(source.pulls, 1)
        self.assertEqual(source.closed, 1)
        self.assertEqual(wire.chunks, [])
        self.assertNotIn("background", wire.history)
        self.assertNoTasks()

    async def testCancellationDuringAsgiStartClosesUnstartedSource(self) -> None:
        """Close the owned source if cancellation interrupts sending headers.

        Returns
        -------
        None
            Verify cancellation closes the source before iteration begins.
        """
        wire = _BlockingStartWire()
        source = _Producer(wire.history)
        response = EventStreamResponse(
            source, background=BackgroundTask(wire.background),
        )
        task = asyncio.create_task(deliver("asgi", wire, response))
        try:
            async with asyncio.timeout(2):
                await wire.starting.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self.assertEqual(source.pulls, 0)
        self.assertEqual(source.closed, 1)
        self.assertNotIn("background", wire.history)
        self.assertNoTasks()

