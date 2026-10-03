import asyncio
import gc
import weakref
from typing import TYPE_CHECKING
import msgspec
from orionis.realtime.config import RealtimeConfig
from orionis.realtime.connection import RealtimeConnection
from orionis.realtime.errors import ClientInvocationError
from orionis.realtime.hub import Hub, HubContext
from orionis.realtime.protocol import Completion, HubProtocol, RPCErrorPayload
from orionis.test import TestCase
from tests.http.test_websocket import _ASGIPeer

if TYPE_CHECKING:
    from collections.abc import Mapping

class _RealtimePeer(_ASGIPeer):
    """Capture complete envelopes and expose a controlled delivery barrier."""

    __slots__ = ("envelopes", "pause_type", "write_entered", "write_release")

    def __init__(self) -> None:
        """
        Prepare deterministic output observation.

        Returns
        -------
        None
            Initialize queues and an initially released write barrier.
        """
        super().__init__()
        self.envelopes = asyncio.Queue()
        self.pause_type: str | None = None
        self.write_entered = asyncio.Event()
        self.write_release = asyncio.Event()
        self.write_release.set()

    async def send(self, event: dict) -> None:
        """
        Decode output and optionally suspend a selected envelope type.

        Parameters
        ----------
        event : dict
            Server ASGI event.

        Returns
        -------
        None
            Record the complete delivered envelope.
        """
        envelope = None
        if event["type"] == "websocket.send":
            envelope = (
                msgspec.json.decode(event["text"]) if "text" in event
                else msgspec.msgpack.decode(event["bytes"])
            )
            if envelope["type"] == self.pause_type:
                self.write_entered.set()
                await self.write_release.wait()
        await super().send(event)
        if envelope is not None:
            self.envelopes.put_nowait(envelope)

    async def nextEnvelope(self) -> dict:
        """
        Wait for the next fully delivered envelope with a finite deadline.

        Returns
        -------
        dict
            Decoded server message.

        Raises
        ------
        TimeoutError
            If no envelope is delivered within two seconds.
        """
        return await asyncio.wait_for(self.envelopes.get(), timeout=2)

    def input(self, envelope: Mapping[str, object], *, binary: bool = False) -> None:
        """
        Queue one encoded client envelope.

        Parameters
        ----------
        envelope : Mapping[str, object]
            Client request or response.
        binary : bool, optional
            Whether to encode MessagePack instead of JSON.

        Returns
        -------
        None
            Add an ASGI receive event.
        """
        payload = (
            {"bytes": msgspec.msgpack.encode(envelope)} if binary
            else {"text": msgspec.json.encode(envelope).decode()}
        )
        self.events.put_nowait({"type": "websocket.receive", **payload})

    def disconnect(self, code: int = 1000, reason: str = "") -> None:
        """
        Queue a terminal peer event.

        Parameters
        ----------
        code : int, optional
            Peer close code.
        reason : str, optional
            Peer close reason.

        Returns
        -------
        None
            Schedule normal reader termination.
        """
        self.events.put_nowait({
            "type": "websocket.disconnect", "code": code, "reason": reason,
        })

class TestRealtimeConnection(TestCase):
    """Check per-connection result ownership and all cleanup exit paths."""

    def setUp(self) -> None:
        """
        Prepare connection tracking.

        Returns
        -------
        None
            Start with no owned connections.
        """
        self.owned_connections: list[RealtimeConnection] = []

    async def asyncTearDown(self) -> None:
        """
        Join remaining work and close every test connection.

        Returns
        -------
        None
            Avoid retaining tasks between tests.
        """
        for connection in self.owned_connections:
            await connection.cleanup()
            await connection.socket.close()

    async def makeConnection(
        self, config: RealtimeConfig | None = None,
    ) -> tuple[_RealtimePeer, RealtimeConnection]:
        """
        Create an accepted connection using the actual raw API.

        Parameters
        ----------
        config : RealtimeConfig | None, optional
            Optional finite resource limits.

        Returns
        -------
        tuple
            Recording peer and a ready, independently owned connection.
        """
        peer = _RealtimePeer()
        socket = peer.socket()
        await socket.accept()
        connection = RealtimeConnection(
            HubContext(connection_id="test-connection", socket=socket),
            Hub, HubProtocol(), config or RealtimeConfig(),
        )
        connection.owner = None
        connection.ready = True
        self.owned_connections.append(connection)
        return peer, connection

    async def testBidirectionalResultsAreCorrelatedOutOfOrder(self) -> None:
        """
        Resolve only the matching future including explicit null results.

        Returns
        -------
        None
            Verify unique compact IDs and out-of-order correlation.
        """
        peer, connection = await self.makeConnection()
        first = asyncio.create_task(connection.invoke("refresh", {"page": 1}))
        second = asyncio.create_task(connection.invoke("refresh", {"page": 2}))
        requests = [await peer.nextEnvelope(), await peer.nextEnvelope()]
        self.assertNotEqual(requests[0]["id"], requests[1]["id"])
        self.assertEqual(len(connection.pending), 2)
        connection.complete(Completion(id=requests[1]["id"], result=None))
        self.assertIsNone(await second)
        self.assertFalse(first.done())
        connection.complete(Completion(id=requests[0]["id"], result={"ok": True}))
        self.assertEqual(await first, {"ok": True})
        self.assertEqual(connection.pending, {})

    async def testDuplicateLateAndForeignCompletionsRetainNothing(self) -> None:
        """
        Ignore completions that do not belong to a live invocation.

        Returns
        -------
        None
            Verify no future or registry growth from unknown completions.
        """
        peer, connection = await self.makeConnection()
        task = asyncio.create_task(connection.invoke("ping"))
        request = await peer.nextEnvelope()
        connection.complete(Completion(id="other-connection", result="wrong"))
        self.assertFalse(task.done())
        connection.complete(Completion(id=request["id"], result="right"))
        self.assertEqual(await task, "right")
        for _ in range(10):
            connection.complete(Completion(id=request["id"], result="duplicate"))
        self.assertEqual(connection.pending, {})

    async def testClientErrorIsSanitizedAndFutureRemoved(self) -> None:
        """
        Avoid propagating untrusted client error text into server exceptions.

        Returns
        -------
        None
            Verify safe client failure and complete registry cleanup.
        """
        peer, connection = await self.makeConnection()
        task = asyncio.create_task(connection.invoke("refresh"))
        request = await peer.nextEnvelope()
        connection.complete(Completion(
            id=request["id"], error=RPCErrorPayload(
                code="client_detail", message="untrusted-private-client-data",
            ),
        ))
        with self.assertRaises(ClientInvocationError) as caught:
            await task
        self.assertEqual(caught.exception.code, "client_error")
        self.assertNotIn("untrusted-private-client-data", str(caught.exception))
        self.assertEqual(connection.pending, {})

    async def testTimeoutAndCallerCancellationRemovePendingFutures(self) -> None:
        """
        Release correlation records on both deadline and task cancellation.

        Returns
        -------
        None
            Verify no pending future remains after either exit.
        """
        peer, connection = await self.makeConnection()
        task = asyncio.create_task(connection.invoke("slow", timeout=0.02))
        request = await peer.nextEnvelope()
        future = connection.pending[request["id"]]
        with self.assertRaises(TimeoutError):
            await task
        self.assertTrue(future.done())
        self.assertEqual(connection.pending, {})
        task = asyncio.create_task(connection.invoke("cancelled"))
        request = await peer.nextEnvelope()
        future = connection.pending[request["id"]]
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(future.done())
        self.assertEqual(connection.pending, {})

    async def testPendingLimitAppliesBeforeWritingAnotherRequest(self) -> None:
        """
        Enforce the finite pending-client-result budget.

        Returns
        -------
        None
            Verify excess invocations do not allocate or send another request.
        """
        peer, connection = await self.makeConnection(RealtimeConfig(
            max_pending_client_invocations=1,
        ))
        first = asyncio.create_task(connection.invoke("waiting"))
        request = await peer.nextEnvelope()
        with self.assertRaises(RuntimeError):
            await connection.invoke("excess")
        self.assertEqual(len(connection.pending), 1)
        self.assertTrue(peer.envelopes.empty())
        connection.complete(Completion(id=request["id"], result=True))
        self.assertTrue(await first)

    async def testDisconnectFailsPendingCallAndReleasesOwnership(self) -> None:
        """
        Complete outstanding client futures when cleanup starts.

        Returns
        -------
        None
            Verify callers wake and all connection registries empty.
        """
        peer, connection = await self.makeConnection()
        task = asyncio.create_task(connection.invoke("waiting"))
        await peer.nextEnvelope()
        await connection.cleanup()
        with self.assertRaises(ConnectionError):
            await task
        self.assertEqual(connection.pending, {})
        self.assertEqual(connection.active, {})
        self.assertIsNone(connection.owner)
        self.assertFalse(connection.ready)
        with self.assertRaises(ConnectionError):
            await connection.invoke("late")

    async def testCancelledCallerDoesNotInterruptTheOwnedFrame(self) -> None:
        """
        Keep an in-flight write intact when its RPC caller is cancelled.

        Returns
        -------
        None
            Verify shielding preserves raw socket state and ordering.
        """
        peer, connection = await self.makeConnection()
        peer.pause_type = "send"
        peer.write_release.clear()
        task = asyncio.create_task(connection.send({"type": "send", "target": "one"}))
        await peer.write_entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertIsNotNone(connection._write_task)
        second = asyncio.create_task(connection.send({"type": "send", "target": "two"}))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        self.assertFalse(connection.socket.closed)
        peer.write_release.set()
        await second
        self.assertEqual((await peer.nextEnvelope())["target"], "one")
        self.assertEqual((await peer.nextEnvelope())["target"], "two")
        self.assertIsNone(connection._write_task)
        await connection.socket.sendText('{"type":"ping"}')

    async def testTimeoutIncludesBlockedDeliveryAndDiscardsLateCompletion(self) -> None:
        """
        Release a pending result even when network backpressure holds its frame.

        Returns
        -------
        None
            Verify the deadline covers delivery and late results are ignored.
        """
        peer, connection = await self.makeConnection()
        peer.pause_type = "invoke"
        peer.write_release.clear()
        task = asyncio.create_task(connection.invoke("slow", timeout=0.02))
        await peer.write_entered.wait()
        with self.assertRaises(TimeoutError):
            await task
        self.assertEqual(connection.pending, {})
        peer.write_release.set()
        request = await peer.nextEnvelope()
        connection.complete(Completion(id=request["id"], result="too late"))
        self.assertEqual(connection.pending, {})

    async def testCleanupCancelsBlockedOwnedWriteWithoutLeakingTask(self) -> None:
        """
        Join a shielded write when its connection is being destroyed.

        Returns
        -------
        None
            Verify cleanup terminates the write and releases its lock.
        """
        peer, connection = await self.makeConnection()
        peer.pause_type = "send"
        peer.write_release.clear()
        caller = asyncio.create_task(connection.send({"type": "send", "target": "x"}))
        await peer.write_entered.wait()
        write = connection._write_task
        if not isinstance(write, asyncio.Task):
            self.fail("Expected an active owned network write")
        await asyncio.wait_for(connection.cleanup(), timeout=1)
        with self.assertRaises(asyncio.CancelledError):
            await caller
        self.assertTrue(write.done())
        self.assertIsNone(connection._write_task)
        self.assertFalse(connection._write_lock.locked())

    async def testCleanupDuringBlockedInvokeReleasesFutureAndWriteCycles(self) -> None:
        """
        Release a pending result even when disconnect interrupts its request frame.

        Returns
        -------
        None
            Verify cleanup retrieves the future error and releases all ownership.
        """
        peer, connection = await self.makeConnection()
        peer.pause_type = "invoke"
        peer.write_release.clear()
        caller = asyncio.create_task(connection.invoke("blocked"))
        await peer.write_entered.wait()
        future = next(iter(connection.pending.values()))
        write = connection._write_task
        if not isinstance(write, asyncio.Task):
            self.fail("Expected an active owned network write")
        references = (weakref.ref(connection), weakref.ref(future), weakref.ref(write))
        await asyncio.wait_for(connection.cleanup(), timeout=1)
        with self.assertRaises(asyncio.CancelledError):
            await caller
        self.assertIsInstance(future.exception(), ConnectionError)
        self.assertEqual(connection.pending, {})
        self.assertTrue(write.done())
        self.assertIsNone(connection._write_task)
        self.assertFalse(connection._write_lock.locked())
        self.owned_connections.remove(connection)
        await connection.socket.close()
        del connection, caller, future, write
        await asyncio.sleep(0)
        gc.collect()
        self.assertTrue(all(reference() is None for reference in references))

    async def testInputValidationPrecedesFutureAllocation(self) -> None:
        """
        Reject invalid targets and deadlines before allocating any state.

        Returns
        -------
        None
            Verify structural validation does not create outbound requests.
        """
        peer, connection = await self.makeConnection()
        for target in ("", "_private", "x.y", "x" * 129):
            with self.assertRaises(ValueError):
                await connection.invoke(target)
        for timeout in (0, -1, True, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                await connection.invoke("valid", timeout=timeout)
        self.assertEqual(connection.pending, {})
        self.assertTrue(peer.envelopes.empty())

    async def testCleanedConnectionDoesNotRetainPendingTaskCycles(self) -> None:
        """
        Allow a cleaned connection and its task references to be collected.

        Returns
        -------
        None
            Verify connection ownership does not create a permanent cycle.
        """
        peer, connection = await self.makeConnection()
        task = asyncio.create_task(connection.invoke("waiting"))
        await peer.nextEnvelope()
        await connection.cleanup()
        with self.assertRaises(ConnectionError):
            await task
        reference = weakref.ref(connection)
        self.owned_connections.remove(connection)
        await connection.socket.close()
        del connection, task
        await asyncio.sleep(0)
        gc.collect()
        self.assertIsNone(reference())
