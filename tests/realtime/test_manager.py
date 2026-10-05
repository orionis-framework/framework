import asyncio
import gc
import weakref
from typing import TYPE_CHECKING, cast
from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
from orionis.realtime.clients import HubClients
from orionis.realtime.entities import BroadcastResult
from orionis.realtime.groups import HubGroups
from orionis.realtime.hub import Hub, HubContext
from orionis.realtime.manager import ConnectionManager
from orionis.realtime.protocol import HubProtocol
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.http.websocket import WebSocket

class _Chat(Hub):
    """Provide an isolated Hub namespace for registry tests."""

    __slots__ = ()

class _OtherChat(Hub):
    """Provide a distinct Hub sharing the same group names."""

    __slots__ = ()

class _Codec(HubProtocol):
    """Count serializations while preserving the production wire encoding."""

    __slots__ = ("encodes",)

    def __init__(self, name: str = "json") -> None:
        """
        Initialize one codec with an empty serialization counter.

        Parameters
        ----------
        name : str, optional
            Production json or msgpack codec name.

        Returns
        -------
        None
            Initialize the real codec and reset the serialization count.
        """
        super().__init__(name)
        self.encodes = 0

    def encode(self, message: object) -> str | bytes:
        """
        Count and encode one envelope using the real codec.

        Parameters
        ----------
        message : object
            Protocol envelope supplied for serialization.

        Returns
        -------
        str | bytes
            Payload encoded by the production codec.
        """
        self.encodes += 1
        return super().encode(message)

class _SendTracker:
    """Observe simultaneous sends while retaining deterministic backpressure."""

    __slots__ = ("active", "expected", "peak", "release", "started")

    def __init__(self, expected: int) -> None:
        """
        Prepare a barrier reached when the configured workers are active.

        Parameters
        ----------
        expected : int
            Concurrent sends required to notify the test.

        Returns
        -------
        None
            Reset concurrency counters and prepare start and release events.
        """
        self.expected = expected
        self.active = 0
        self.peak = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

class _Connection:
    """Record delivery without introducing background tasks or pending futures."""

    __slots__ = (
        "__weakref__", "closing", "context", "fail", "hub", "invoked", "on_send",
        "protocol", "ready", "sent", "tracker",
    )

    def __init__(
        self,
        identifier: str,
        hub: type[Hub] = _Chat,
        protocol: HubProtocol | None = None,
        tracker: _SendTracker | None = None,
    ) -> None:
        """
        Store the immutable identity and fake the unused context socket.

        Parameters
        ----------
        identifier : str
            Connection identity used by registry selections.
        hub : type[Hub], optional
            Owning Hub namespace.
        protocol : HubProtocol | None, optional
            Codec to use, or None for a counting JSON codec.
        tracker : _SendTracker | None, optional
            Optional send concurrency and backpressure tracker.

        Returns
        -------
        None
            Initialize ready state, delivery journals and optional tracking.
        """
        self.context = HubContext(
            connection_id=identifier, socket=cast("WebSocket", None),
        )
        self.hub = hub
        self.protocol = protocol if protocol is not None else _Codec()
        self.ready = True
        self.closing = False
        self.fail = False
        self.sent: list[str | bytes] = []
        self.invoked: list[tuple[str, tuple[object, ...], float | None]] = []
        self.tracker = tracker
        self.on_send: Callable[[], None] | None = None

    async def sendEncoded(self, data: str | bytes) -> None:
        """
        Record a frame after optional simulated network backpressure.

        Parameters
        ----------
        data : str | bytes
            Already encoded transport frame.

        Returns
        -------
        None
            Record delivery and run the configured post-send callback.

        Raises
        ------
        ConnectionError
            If the fixture is configured as a disconnected recipient.
        """
        tracker = self.tracker
        if tracker is not None:
            tracker.active += 1
            tracker.peak = max(tracker.peak, tracker.active)
            if tracker.active == tracker.expected:
                tracker.started.set()
        try:
            if tracker is not None:
                await tracker.release.wait()
            if self.fail:
                error_msg = "Simulated disconnected recipient"
                raise ConnectionError(error_msg)
            self.sent.append(data)
            if self.on_send is not None:
                self.on_send()
        finally:
            if tracker is not None:
                tracker.active -= 1

    async def invoke(
        self, target: str, *args: object,
        timeout: float | None = None,  # noqa: ASYNC109 - Record forwarding semantics.
    ) -> object:
        """
        Record one client call and return a deterministic result.

        Parameters
        ----------
        target : str
            Forwarded client method name.
        *args : object
            Forwarded positional values.
        timeout : float | None, optional
            Forwarded deadline, recorded without enforcing it.

        Returns
        -------
        object
            Mapping identifying the fixture connection.
        """
        self.invoked.append((target, args, timeout))
        return {"source": self.context.connection_id}

class TestConnectionManager(TestCase):
    """Exercise registry ownership, bounded delivery and cleanup invariants."""

    def testGroupsRemainHubLocalAndProvisionalConnectionsAreNotTargets(self) -> None:
        """
        Permit initialization membership without prematurely exposing recipients.

        Returns
        -------
        None
            Verify Hub isolation, readiness filtering and idempotent removal.
        """
        manager = ConnectionManager(RealtimeConfig())
        first = _Connection("first")
        first.ready = False
        other = _Connection("other", _OtherChat)
        for connection in (first, other):
            manager.register(connection)
            manager.join(connection.context.connection_id, "general")
        self.assertEqual(manager.snapshot(), (first, other))
        self.assertEqual(manager.connectionCount, 2)
        self.assertEqual(manager.groupCount, 2)
        self.assertIsNone(manager.get("first"))
        self.assertEqual(manager.groupIds(_Chat, "general"), ())
        self.assertEqual(manager.groupIds(_OtherChat, "general"), ("other",))
        first.ready = True
        self.assertEqual(manager.groupIds(_Chat, "general"), ("first",))
        self.assertIsNone(manager.get("other", _Chat))
        first.closing = True
        self.assertEqual(manager.connectionIds(_Chat), ())
        for connection in (first, other):
            manager.unregister(connection)
            manager.unregister(connection)
        self.assertEqual(manager.connectionCount, 0)
        self.assertEqual(manager.groupCount, 0)
        self.assertEqual(manager._hubs, {})
        self.assertEqual(manager._memberships, {})

    async def testTargetsIsolateHubsDeduplicateClientsAndReturnResults(self) -> None:
        """
        Deliver all, caller, others, selected clients and groups consistently.

        Returns
        -------
        None
            Verify recipient selection, deduplication and single-client results.
        """
        manager = ConnectionManager(RealtimeConfig())
        first = _Connection("first")
        second = _Connection("second")
        other = _Connection("other", _OtherChat)
        for connection in (first, second, other):
            manager.register(connection)
            manager.join(connection.context.connection_id, "room")
        clients = HubClients(manager, _Chat, "first")
        self.assertEqual(await clients.all.send("notice", 1), BroadcastResult(sent=2))
        self.assertEqual(await clients.caller.send("notice"), BroadcastResult(sent=1))
        self.assertEqual(await clients.others.send("notice"), BroadcastResult(sent=1))
        self.assertEqual(await clients.group("room").send("notice"),
                         BroadcastResult(sent=2))
        self.assertEqual(
            await clients.clients(["first", "first", "second", "other"]).send("notice"),
            BroadcastResult(sent=2, failed=1),
        )
        self.assertEqual(other.sent, [])
        self.assertEqual(len(first.sent), 4)
        self.assertEqual(len(second.sent), 4)
        self.assertEqual(
            await clients.client("missing").send("notice"), BroadcastResult(failed=1),
        )
        result = await clients.client("first").invoke("refresh", 3, timeout=5)
        self.assertEqual(result, {"source": "first"})
        self.assertEqual(first.invoked, [("refresh", (3,), 5)])
        with self.assertRaises(ConnectionError):
            await clients.client("other").invoke("refresh")
        with self.assertRaises(RuntimeError):
            await clients.clients(["first"]).invoke("refresh")
        with self.assertRaises(RuntimeError):
            await clients.all.invoke("refresh")
        outside = manager.hub(_Chat)
        for attribute in ("caller", "others"):
            with self.subTest(attribute=attribute), self.assertRaises(RuntimeError):
                getattr(outside, attribute)

    async def testGroupLimitsAndMembershipCleanup(self) -> None:
        """
        Bound distinct memberships and release empty groups immediately.

        Returns
        -------
        None
            Verify repeated joins, membership limits and disconnection cleanup.
        """
        manager = ConnectionManager(RealtimeConfig(max_groups_per_connection=2))
        connection = _Connection("first")
        manager.register(connection)
        groups = HubGroups(manager, "first")
        await groups.join("one")
        await groups.join("one")
        await groups.join("two")
        with self.assertRaises(RuntimeError):
            await groups.join("three")
        await groups.leave("one")
        await groups.leave("one")
        await groups.join("three")
        self.assertEqual(manager.groupCount, 2)
        manager.unregister(connection)
        await groups.leave("three")
        self.assertEqual(manager.groupCount, 0)
        with self.assertRaises(ConnectionError):
            await groups.join("again")

    async def testBroadcastBoundsWorkersAndIsolatesRecipientFailures(self) -> None:
        """
        Honor a fixed concurrency cap even when some connections fail.

        Returns
        -------
        None
            Verify bounded workers, isolated failures and task release.
        """
        manager = ConnectionManager(RealtimeConfig(broadcast_concurrency=3))
        tracker = _SendTracker(3)
        connections = [_Connection(f"client-{i}", tracker=tracker) for i in range(25)]
        connections[5].fail = True
        for connection in connections:
            manager.register(connection)
        before = asyncio.all_tasks()
        delivery = asyncio.create_task(manager.hub(_Chat).all.send("notice", {"a": 1}))
        try:
            async with asyncio.timeout(2):
                await tracker.started.wait()
            self.assertEqual(tracker.active, 3)
            self.assertLessEqual(len(asyncio.all_tasks() - before), 4)
        finally:
            tracker.release.set()
        self.assertEqual(await delivery, BroadcastResult(sent=24, failed=1))
        self.assertEqual(tracker.peak, 3)
        self.assertEqual(tracker.active, 0)
        self.assertEqual(asyncio.all_tasks() - before, set())

    async def testBroadcastCancellationReleasesEveryWorker(self) -> None:
        """
        Propagate cancellation without leaving send tasks or registry copies.

        Returns
        -------
        None
            Verify every broadcast worker releases its tracked send state.
        """
        manager = ConnectionManager(RealtimeConfig(broadcast_concurrency=2))
        tracker = _SendTracker(2)
        for index in range(8):
            manager.register(_Connection(f"client-{index}", tracker=tracker))
        before = asyncio.all_tasks()
        delivery = asyncio.create_task(manager.hub(_Chat).all.send("notice"))
        async with asyncio.timeout(2):
            await tracker.started.wait()
        delivery.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await delivery
        self.assertEqual(tracker.active, 0)
        self.assertEqual(asyncio.all_tasks() - before, set())

    async def testBroadcastSerializesOncePerCodecAndSharesImmutableFrames(self) -> None:
        """
        Reuse one frame for each encoding across independent codec instances.

        Returns
        -------
        None
            Verify one serialization per codec and shared immutable payloads.
        """
        manager = ConnectionManager(RealtimeConfig())
        json_codec = _Codec()
        second_json = _Codec()
        msgpack_codec = _Codec("msgpack")
        connections = [
            _Connection("first", protocol=json_codec),
            _Connection("second", protocol=second_json),
            _Connection("binary", protocol=msgpack_codec),
        ]
        for connection in connections:
            manager.register(connection)
        result = await manager.hub(_Chat).clients(
            ["first", "second", "binary"],
        ).send("notice", {"text": "¡Hola!"})
        self.assertEqual(result, BroadcastResult(sent=3))
        self.assertEqual(json_codec.encodes + second_json.encodes, 1)
        self.assertEqual(msgpack_codec.encodes, 1)
        self.assertIs(connections[0].sent[0], connections[1].sent[0])
        self.assertIsInstance(connections[2].sent[0], bytes)

    async def testSerializationFailureSendsNothing(self) -> None:
        """
        Fail encoding before any recipient sees a partial broadcast.

        Returns
        -------
        None
            Verify an unsupported value prevents all transport writes.
        """
        manager = ConnectionManager(RealtimeConfig())
        connection = _Connection("first")
        manager.register(connection)
        with self.assertRaises(TypeError):
            await manager.hub(_Chat).all.send("notice", object())
        self.assertEqual(connection.sent, [])

    async def testDisconnectedRecipientsReleaseReferences(self) -> None:
        """
        Recheck availability before sending to each snapshotted identifier.

        Returns
        -------
        None
            Verify missing recipients fail delivery and release group references.
        """
        manager = ConnectionManager(RealtimeConfig(broadcast_concurrency=1))
        first = _Connection("first")
        second = _Connection("second")
        first.on_send = lambda connection=second: manager.unregister(connection)
        manager.register(first)
        manager.register(second)
        manager.join("second", "room")
        result = await manager.hub(_Chat).clients(["first", "second"]).send("notice")
        self.assertEqual(result, BroadcastResult(sent=1, failed=1))
        self.assertEqual(second.sent, [])
        self.assertEqual(manager.groupCount, 0)
        first.on_send = None
        reference = weakref.ref(second)
        del second
        gc.collect()
        self.assertIsNone(reference())

    def testRegistryRejectsDuplicateOwnershipAndValidatesPublicSelections(self) -> None:
        """
        Keep identity and bounded identifier checks ahead of registry writes.

        Returns
        -------
        None
            Verify duplicate ownership and invalid client selections are rejected.
        """
        manager = ConnectionManager(RealtimeConfig())
        connection = _Connection("first")
        manager.register(connection)
        duplicate = _Connection("first")
        with self.assertRaises(ValueError):
            manager.register(duplicate)
        manager.unregister(duplicate)
        self.assertIs(manager.get("first"), connection)
        clients = manager.hub(_Chat)
        for identifier in ("", " ", "x" * 129):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                clients.client(identifier)
        for group in ("", " ", "x" * 257):
            with self.subTest(group=group), self.assertRaises(ValueError):
                clients.group(group)
        with self.assertRaises(TypeError):
            clients.clients("first")
        with self.assertRaises(TypeError):
            manager.hub(cast("type[Hub]", object))

    async def testClientTargetsRejectPrivateNamesAndOversizedArguments(self) -> None:
        """
        Validate outbound method metadata before touching any connection.

        Returns
        -------
        None
            Verify private targets and oversized argument lists fail eagerly.
        """
        clients = ConnectionManager(RealtimeConfig()).hub(_Chat)
        for target in ("_private", "module.method", "x" * 129, "", "not a name"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                await clients.all.send(target)
        with self.assertRaises(ValueError):
            await clients.all.send("notice", *range(65))
