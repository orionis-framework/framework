import asyncio
from collections.abc import AsyncIterator  # noqa: TC003 - Hub annotation reflection.
from typing import TYPE_CHECKING, cast
import msgspec
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context, current_auth_context
from orionis.auth.exceptions import AuthenticationException, AuthorizationException
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext, get_current_scope
from orionis.http import WebSocket  # noqa: TC001 - Runtime method injection.
from orionis.realtime.config import RealtimeConfig
from orionis.realtime.connection import RealtimeConnection
from orionis.realtime.decorators import remote
from orionis.realtime.hub import Hub, HubContext
from orionis.realtime.manager import ConnectionManager
from orionis.realtime.runtime import HubRuntime
from orionis.test import TestCase
from tests.realtime.test_connection import _RealtimePeer

if TYPE_CHECKING:
    from orionis.container.context.manager import ScopeManager
    from orionis.foundation.contracts.application import IApplication

class _Marker:
    """Represent a mutable dependency that must remain invocation-local."""

    __slots__ = ("label",)

    def __init__(self) -> None:
        """
        Initialize the unset invocation marker.

        Returns
        -------
        None
            Prepare independently mutable state.
        """
        self.label = ""

class _Payload(msgspec.Struct, forbid_unknown_fields=True):
    """Require structurally typed client data."""

    name: str
    amount: int

class _Probe:
    """Collect lifecycle evidence while coordinating concurrent invocations."""

    __slots__ = (
        "calls", "close_entered", "close_release", "closed_stream", "disconnects",
        "entered", "hubs", "produced", "release", "settled",
    )

    def __init__(self) -> None:
        """
        Create isolated observation lists and deterministic barriers.

        Returns
        -------
        None
            Prepare test-owned state independent of connection scopes.
        """
        self.calls = []
        self.disconnects = []
        self.hubs = []
        self.produced = []
        self.entered = asyncio.Queue()
        self.release = asyncio.Event()
        self.closed_stream = asyncio.Event()
        self.close_entered = asyncio.Event()
        self.close_release = asyncio.Event()
        self.settled = []

class _ClosableItems:
    """Model asynchronous iterator cleanup that remains pending after exhaustion."""

    __slots__ = ("_mode", "_probe", "_sent")

    def __init__(self, probe: _Probe, mode: str) -> None:
        """
        Configure a one-item iterator and its explicit close behavior.

        Parameters
        ----------
        probe : _Probe
            Test-owned synchronization and observation state.
        mode : str
            Whether closing fails or waits for a barrier.

        Returns
        -------
        None
            Prepare one item and an independently observable finalizer.
        """
        self._probe = probe
        self._mode = mode
        self._sent = False

    def __aiter__(self) -> _ClosableItems:
        """
        Return the single-consumer iterator.

        Returns
        -------
        _ClosableItems
            This iterator.
        """
        return self

    async def __anext__(self) -> int:
        """
        Yield one item before reporting exhaustion.

        Returns
        -------
        int
            The sole stream value.

        Raises
        ------
        StopAsyncIteration
            After the single value has been produced.
        """
        if self._sent:
            raise StopAsyncIteration
        self._sent = True
        return 42

    async def aclose(self) -> None:
        """
        Expose failure or delayed completion after iteration has ended.

        Returns
        -------
        None
            Complete asynchronous finalization when the test permits it.

        Raises
        ------
        RuntimeError
            When this fixture is configured to fail during finalization.
        """
        self._probe.close_entered.set()
        if self._mode == "fail":
            message = "private iterator cleanup failure"
            raise RuntimeError(message)
        await self._probe.close_release.wait()
        self._probe.closed_stream.set()

class _ReplyingPeer(_RealtimePeer):
    """Reuse an invocation ID immediately when its terminal reaches the network."""

    __slots__ = ("replied",)

    def __init__(self) -> None:
        """
        Enable one immediate client reply from inside the server write callback.

        Returns
        -------
        None
            Prepare deterministic ID reuse before the sending task returns.
        """
        super().__init__()
        self.replied = False

    async def send(self, event: dict) -> None:
        """
        Deliver a terminal and reenter the reader before the writer resumes.

        Parameters
        ----------
        event : dict
            Server ASGI event.

        Returns
        -------
        None
            Reuse the terminal's ID for a second invocation exactly once.
        """
        await super().send(event)
        if event["type"] != "websocket.send" or "text" not in event:
            return
        envelope = msgspec.json.decode(event["text"])
        if (
            envelope["type"] == "completion" and envelope["id"] == "reused"
            and not self.replied
        ):
            self.replied = True
            self.input({
                "type": "invoke", "id": "reused", "target": "defaults", "args": [99],
            })
            await asyncio.sleep(0)

class _RuntimeHub(Hub):
    """Exercise constructor injection, RPC data and per-invocation services."""

    __slots__ = ("marker", "probe")

    def __init__(self, probe: _Probe, marker: _Marker) -> None:
        """
        Retain constructor-injected services for identity assertions.

        Parameters
        ----------
        probe : _Probe
            Test-owned singleton coordination service.
        marker : _Marker
            Mutable dependency scoped to this construction.

        Returns
        -------
        None
            Record this independently built Hub.
        """
        self.probe = probe
        self.marker = marker
        probe.hubs.append(self)

    async def onConnect(self) -> None:
        """
        Join a provisional connection to an application group.

        Returns
        -------
        None
            Record connection-scope state before ready is emitted.
        """
        self.probe.calls.append(("connect", self.marker, get_current_scope()))
        await self.groups.join("runtime-test")

    async def onDisconnect(self, code: int, reason: str | None = None) -> None:
        """
        Record final hook details for cleanup assertions.

        Parameters
        ----------
        code : int
            Peer or local close code.
        reason : str | None, optional
            Available close reason.

        Returns
        -------
        None
            Record hook metadata and its remaining connection scope.
        """
        self.probe.disconnects.append((code, reason, get_current_scope()))

    @remote
    async def echo(
        self, value: str, marker: _Marker, socket: WebSocket, context: HubContext,
    ) -> dict:
        """
        Validate constructor, method and framework context injection.

        Parameters
        ----------
        value : str
            Client-controlled value.
        marker : _Marker
            Container-owned scoped dependency.
        socket : WebSocket
            Framework-owned connection.
        context : HubContext
            Framework-owned identity and metadata.

        Returns
        -------
        dict
            Echo result and verified dependency identity.
        """
        self.probe.calls.append(("echo", marker, get_current_scope()))
        return {
            "value": value, "same_marker": marker is self.marker,
            "same_socket": socket is self.context.socket,
            "same_context": context is self.context,
        }

    @remote
    async def defaults(self, value: int = 7) -> int:
        """
        Return an optional client value.

        Parameters
        ----------
        value : int, optional
            Client value with a server-defined default.

        Returns
        -------
        int
            Supplied or default value.
        """
        return value

    @remote
    async def validated(self, payload: _Payload) -> int:
        """
        Accept only a validated schema instance.

        Parameters
        ----------
        payload : _Payload
            Client data converted by the explicit RPC binder.

        Returns
        -------
        int
            Schema value after successful conversion.
        """
        return payload.amount

    @remote
    async def gated(self, label: str, marker: _Marker) -> str:
        """
        Suspend while another invocation mutates its own scoped dependency.

        Parameters
        ----------
        label : str
            Client marker identifying this invocation.
        marker : _Marker
            Mutable scoped service.

        Returns
        -------
        str
            State retained by this invocation's unique dependency.
        """
        marker.label = label
        self.probe.calls.append((
            label, marker, get_current_scope(), current_auth_context(),
        ))
        self.probe.entered.put_nowait(label)
        try:
            await self.probe.release.wait()
            return marker.label
        finally:
            self.probe.settled.append(label)

    @remote
    async def fail(self, kind: str = "internal") -> None:
        """
        Raise application or auth failures to exercise safe error mapping.

        Parameters
        ----------
        kind : str, optional
            Requested test failure category.

        Returns
        -------
        None
            Raise the selected application failure.

        Raises
        ------
        AuthenticationException
            If the requested failure category is unauthorized.
        AuthorizationException
            If the requested failure category is forbidden.
        ValueError
            For all other categories, simulating an internal application failure.
        """
        message = "private_database_key_and_traceback"
        if kind == "unauthorized":
            raise AuthenticationException(message)
        if kind == "forbidden":
            raise AuthorizationException(message)
        raise ValueError(message)

    @remote
    async def stream(self, count: int) -> AsyncIterator[int]:
        """
        Produce one item only after the previous delivery has completed.

        Parameters
        ----------
        count : int
            Number of sequence items to produce.

        Yields
        ------
        int
            Sequential value whose delivery must precede the next item.
        """
        try:
            for item in range(count):
                self.probe.produced.append(item)
                yield item
        finally:
            self.probe.closed_stream.set()

    @remote
    async def broadStream(self) -> object:
        """
        Return a stream whose broad annotation cannot declare its lifetime.

        Returns
        -------
        object
            Asynchronous iterable discovered from the runtime result.
        """
        return self._delayedStream()

    @remote
    async def closingStream(self, mode: str) -> object:
        """
        Return an iterator whose close operation needs explicit lifecycle handling.

        Parameters
        ----------
        mode : str
            Select failing or blocked finalization.

        Returns
        -------
        object
            Custom asynchronous iterable with an explicit aclose operation.
        """
        return _ClosableItems(self.probe, mode)

    async def _delayedStream(self) -> AsyncIterator[int]:
        """
        Pause the producer until the test explicitly releases it.

        Yields
        ------
        int
            One value after the invocation's ordinary deadline has passed.
        """
        self.probe.entered.put_nowait("broad-stream")
        try:
            await self.probe.release.wait()
            yield 42
        finally:
            self.probe.closed_stream.set()

    @remote
    async def callClient(self) -> object:
        """
        Invoke the calling client while the reader remains independently active.

        Returns
        -------
        object
            Correlated client result.
        """
        return await self.clients.caller.invoke("refresh", {"section": "orders"})

    async def hidden(self) -> str:
        """
        Define a public method deliberately unavailable to RPC.

        Returns
        -------
        str
            Value that must never be exposed automatically.
        """
        return "not remotely exposed"

class _RejectingHub(_RuntimeHub):
    """Reject a connection before its raw handshake is accepted."""

    __slots__ = ()

    async def onConnect(self) -> None:
        """
        Reject unauthorized admission before emitting a ready envelope.

        Returns
        -------
        None
            Deny the pending handshake.
        """
        await self.context.socket.reject(401)

class _TrackedContainer(Container):
    """Use the real contextvars container while retaining scope lifetimes."""

    __slots__ = ("scopes",)

    def __init__(self) -> None:
        """
        Initialize the ordinary container and scope recorder.

        Returns
        -------
        None
            Prepare the isolated test application.
        """
        super().__init__()
        self.scopes = []

    def beginScope(self) -> ScopeManager:
        """
        Record an independent container scope.

        Returns
        -------
        ScopeManager
            New contextvars-backed scope.
        """
        scope = super().beginScope()
        self.scopes.append(scope)
        return scope

class TestHubRuntime(TestCase):
    """Exercise complete Hub connections with the real DI container."""

    def setUp(self) -> None:
        """
        Register fixture services outside the runner's ambient scope.

        Returns
        -------
        None
            Prepare globally registered services in an isolated container.
        """
        self.ambient = get_current_scope()
        ScopedContext.setCurrentScope(None)
        self.app = _TrackedContainer()
        self.probe = _Probe()
        self.app.instance(None, self.probe)
        self.app.scoped(None, _Marker)
        self.owned_tasks: list[asyncio.Task[None]] = []

    async def asyncTearDown(self) -> None:
        """
        Cancel remaining connection owners and join their cleanup.

        Returns
        -------
        None
            Finish connection tasks before disposing the test container.
        """
        for task in self.owned_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.owned_tasks, return_exceptions=True)

    def tearDown(self) -> None:
        """
        Restore the runner scope and remove the isolated singleton container.

        Returns
        -------
        None
            Release fixture registration state.
        """
        Container._instances.pop(_TrackedContainer, None)
        ScopedContext.setCurrentScope(self.ambient)

    async def _serve(self, runtime: HubRuntime, socket: WebSocket) -> None:
        """
        Emulate the kernel's connection scope using the actual container.

        Parameters
        ----------
        runtime : HubRuntime
            Compiled Hub execution engine.
        socket : WebSocket
            Raw connection supplied by the transport adapter.

        Returns
        -------
        None
            Keep the connection scope alive through final cleanup.
        """
        async with self.app.beginScope():
            bind_auth_context(AuthenticationContext())
            await runtime.serve(socket)

    async def connect(
        self, config: RealtimeConfig | None = None,
        hub: type[Hub] = _RuntimeHub, protocol: str = "json",
        peer: _RealtimePeer | None = None,
    ) -> tuple[_RealtimePeer, ConnectionManager, asyncio.Task, dict]:
        """
        Start a Hub owner and wait for its ready envelope.

        Parameters
        ----------
        config : RealtimeConfig | None, optional
            Limits to apply to this registry and connection.
        hub : type[Hub], optional
            Registered application Hub type.
        protocol : str, optional
            Route-selected serializer.
        peer : _RealtimePeer | None, optional
            Optional specialized transport peer used to exercise delivery races.

        Returns
        -------
        tuple
            Peer, registry, running owner and ready envelope.
        """
        manager = ConnectionManager(config or RealtimeConfig())
        runtime = HubRuntime(cast("IApplication", self.app), manager, hub, protocol)
        peer = peer or _RealtimePeer()
        task = asyncio.create_task(self._serve(runtime, peer.socket()))
        self.owned_tasks.append(task)
        ready = await peer.nextEnvelope()
        self.assertEqual(ready["type"], "ready")
        self.assertEqual(ready["version"], 1)
        # A round trip observes readiness after shielded handshake delivery.
        peer.input({"type": "ping"}, binary=protocol == "msgpack")
        self.assertEqual(await peer.nextEnvelope(), {"type": "pong"})
        return peer, manager, task, ready

    def connection(
        self, manager: ConnectionManager, connection_id: str,
    ) -> RealtimeConnection:
        """
        Narrow the registry contract to the concrete connection under test.

        Parameters
        ----------
        manager : ConnectionManager
            Local registry used by this runtime.
        connection_id : str
            Identifier delivered by the ready envelope.

        Returns
        -------
        RealtimeConnection
            Concrete ready connection whose ownership can be inspected.
        """
        connection = manager.get(connection_id)
        if not isinstance(connection, RealtimeConnection):
            self.fail("Expected a ready connection created by HubRuntime")
        return connection

    async def settle(self, manager: ConnectionManager, connection_id: str) -> None:
        """
        Join invocations after observing their final delivered envelope.

        Parameters
        ----------
        manager : ConnectionManager
            Registry owning the observed connection.
        connection_id : str
            Ready connection whose invocations just produced terminal messages.

        Returns
        -------
        None
            Wait for coroutine finalizers following transport delivery.
        """
        connection = self.connection(manager, connection_id)
        tasks = {*connection.active.values(), *connection.finishing}
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=2,
        )

    async def testLifecycleDiBindingAndIndependentInvocationScope(self) -> None:
        """
        Resolve constructor and method dependencies within a fresh invocation.

        Returns
        -------
        None
            Verify ready, DI identity, scope disposal and disconnect metadata.
        """
        peer, manager, task, ready = await self.connect()
        self.assertGreaterEqual(len(ready["connection_id"]), 24)
        peer.input({"type": "invoke", "id": "one", "target": "echo", "args": ["hi"]})
        completion = await peer.nextEnvelope()
        self.assertEqual(completion["result"], {
            "value": "hi", "same_marker": True,
            "same_socket": True, "same_context": True,
        })
        await self.settle(manager, ready["connection_id"])
        connect, invocation = self.probe.calls
        self.assertIsNot(connect[1], invocation[1])
        self.assertIsNot(connect[2], invocation[2])
        self.assertFalse(invocation[2].isActive)
        self.assertTrue(connect[2].isActive)
        peer.disconnect(1001, "leaving")
        await asyncio.wait_for(task, timeout=2)
        self.assertEqual(manager.connectionCount, 0)
        self.assertEqual(manager.groupCount, 0)
        self.assertEqual(self.probe.disconnects[0][:2], (1001, "leaving"))
        self.assertTrue(all(not scope.isActive for scope in self.app.scopes))
        self.assertIsNot(self.probe.hubs[0], self.probe.hubs[1])

    async def testConcurrentInvocationsIsolateServicesAndAuth(self) -> None:
        """
        Keep mutable scoped services and authentication contexts independent.

        Returns
        -------
        None
            Verify overlapping invocations do not overwrite one another's state.
        """
        peer, manager, _task, ready = await self.connect()
        for label in ("first", "second"):
            peer.input({
                "type": "invoke", "id": label, "target": "gated", "args": [label],
            })
        await asyncio.wait_for(self.probe.entered.get(), timeout=2)
        await asyncio.wait_for(self.probe.entered.get(), timeout=2)
        first, second = self.probe.calls[-2:]
        for index in (1, 2, 3):
            self.assertIsNot(first[index], second[index])
        self.probe.release.set()
        results = [await peer.nextEnvelope(), await peer.nextEnvelope()]
        self.assertEqual({item["id"]: item["result"] for item in results}, {
            "first": "first", "second": "second",
        })
        await self.settle(manager, ready["connection_id"])
        self.assertFalse(first[2].isActive)
        self.assertFalse(second[2].isActive)

    async def testOnlyRegisteredRemoteMethodsCanRun(self) -> None:
        """
        Reject public, private and dotted method lookup outside dispatch metadata.

        Returns
        -------
        None
            Verify unknown targets are controlled errors and the socket survives.
        """
        peer, _manager, _task, _ready = await self.connect()
        targets = ("hidden", "__class__", "os.system", "onConnect")
        for index, target in enumerate(targets):
            peer.input({"type": "invoke", "id": str(index), "target": target})
            self.assertEqual(
                (await peer.nextEnvelope())["error"]["code"], "method_not_found",
            )
        peer.input({"type": "invoke", "id": "valid", "target": "defaults"})
        self.assertEqual((await peer.nextEnvelope())["result"], 7)

    async def testClientCannotReplaceContainerOrFrameworkArguments(self) -> None:
        """
        Filter named arguments before dispatching through Application.call.

        Returns
        -------
        None
            Verify DI injection is protected from client-supplied names.
        """
        peer, _manager, _task, _ready = await self.connect()
        for name in ("marker", "socket", "context"):
            peer.input({
                "type": "invoke", "id": name, "target": "echo",
                "args": ["valid"], "kwargs": {name: "attacker"},
            })
            self.assertEqual(
                (await peer.nextEnvelope())["error"]["code"], "invalid_arguments",
            )
        self.assertEqual(len(self.probe.calls), 1)

    async def testSchemaErrorsAndApplicationErrorsRemainInvocationLocal(self) -> None:
        """
        Report sanitized failures without terminating a healthy connection.

        Returns
        -------
        None
            Verify schema validation and safe internal/auth error classification.
        """
        peer, _manager, _task, _ready = await self.connect()
        peer.input({
            "type": "invoke", "id": "invalid", "target": "validated",
            "args": [{"name": "test", "amount": "not-an-int"}],
        })
        self.assertEqual(
            (await peer.nextEnvelope())["error"]["code"], "validation_error",
        )
        for kind in ("internal", "unauthorized", "forbidden"):
            peer.input({
                "type": "invoke", "id": kind, "target": "fail", "args": [kind],
            })
            result = await peer.nextEnvelope()
            expected = "internal_error" if kind == "internal" else kind
            self.assertEqual(result["error"]["code"], expected)
            self.assertNotIn("private_database_key", str(result))
        peer.input({
            "type": "invoke", "id": "valid", "target": "validated",
            "args": [{"name": "test", "amount": 9}],
        })
        self.assertEqual((await peer.nextEnvelope())["result"], 9)

    async def testBidirectionalRpcKeepsReaderAvailableForCompletion(self) -> None:
        """
        Receive a client result while its originating Hub invocation is pending.

        Returns
        -------
        None
            Verify authentic server-to-client RPC without reader deadlock.
        """
        peer, manager, _task, ready = await self.connect()
        peer.input({"type": "invoke", "id": "client-call", "target": "callClient"})
        outgoing = await peer.nextEnvelope()
        self.assertEqual(outgoing["type"], "invoke")
        self.assertEqual(outgoing["target"], "refresh")
        peer.input({"type": "completion", "id": outgoing["id"], "result": {"ok": True}})
        result = await peer.nextEnvelope()
        self.assertEqual(result, {
            "type": "completion", "id": "client-call", "result": {"ok": True},
        })
        connection = self.connection(manager, ready["connection_id"])
        self.assertEqual(connection.pending, {})

    async def testStreamingPreservesBackpressureAndClosesGenerator(self) -> None:
        """
        Advance the producer only after each item reaches the transport.

        Returns
        -------
        None
            Verify strict item ordering and generator finalization.
        """
        peer, _manager, _task, _ready = await self.connect()
        peer.pause_type = "stream_item"
        peer.write_release.clear()
        peer.input({"type": "invoke", "id": "stream", "target": "stream", "args": [2]})
        await asyncio.wait_for(peer.write_entered.wait(), timeout=2)
        self.assertEqual(self.probe.produced, [0])
        self.assertTrue(peer.envelopes.empty())
        peer.write_release.set()
        output = [await peer.nextEnvelope() for _ in range(3)]
        self.assertEqual([item["type"] for item in output], [
            "stream_item", "stream_item", "stream_complete",
        ])
        self.assertEqual([item["item"] for item in output[:2]], [0, 1])
        self.assertTrue(self.probe.closed_stream.is_set())

    async def testBroadStreamOutlivesOrdinaryInvocationTimeout(self) -> None:
        """
        Remove the ordinary deadline after discovering an AsyncIterable result.

        Returns
        -------
        None
            Verify broad annotations do not truncate a long-lived stream.
        """
        peer, manager, _task, ready = await self.connect(RealtimeConfig(
            invocation_timeout=0.02,
        ))
        peer.input({"type": "invoke", "id": "broad", "target": "broadStream"})
        await asyncio.wait_for(self.probe.entered.get(), timeout=2)
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(peer.envelopes.get(), timeout=0.08)
        self.assertFalse(self.probe.closed_stream.is_set())
        self.probe.release.set()
        self.assertEqual(await peer.nextEnvelope(), {
            "type": "stream_item", "id": "broad", "item": 42,
        })
        self.assertEqual(await peer.nextEnvelope(), {
            "type": "stream_complete", "id": "broad",
        })
        await self.settle(manager, ready["connection_id"])
        self.assertTrue(self.probe.closed_stream.is_set())

    async def testBroadStreamStillHonorsAnExplicitClientTimeout(self) -> None:
        """
        Retain an explicitly requested deadline for dynamically detected streams.

        Returns
        -------
        None
            Verify disabling the default does not disable a client stream deadline.
        """
        peer, manager, _task, ready = await self.connect()
        peer.input({
            "type": "invoke", "id": "bounded", "target": "broadStream",
            "timeout": 0.02,
        })
        await asyncio.wait_for(self.probe.entered.get(), timeout=2)
        terminal = await peer.nextEnvelope()
        self.assertEqual(terminal["type"], "stream_complete")
        self.assertEqual(terminal["id"], "bounded")
        self.assertEqual(terminal["error"]["code"], "timeout")
        await self.settle(manager, ready["connection_id"])
        self.assertTrue(self.probe.closed_stream.is_set())

    async def testIteratorCloseFailureProducesOnlyOneErrorTerminal(self) -> None:
        """
        Treat asynchronous finalizer failure as the stream's sole terminal outcome.

        Returns
        -------
        None
            Verify successful stream completion cannot precede aclose failure.
        """
        peer, manager, _task, ready = await self.connect()
        peer.input({
            "type": "invoke", "id": "close-fails", "target": "closingStream",
            "args": ["fail"],
        })
        self.assertEqual((await peer.nextEnvelope())["type"], "stream_item")
        terminal = await peer.nextEnvelope()
        self.assertEqual(terminal["type"], "stream_complete")
        self.assertEqual(terminal["error"]["code"], "internal_error")
        self.assertNotIn("private iterator", str(terminal))
        await self.settle(manager, ready["connection_id"])
        peer.input({"type": "ping"})
        self.assertEqual(await peer.nextEnvelope(), {"type": "pong"})
        self.assertTrue(peer.envelopes.empty())

    async def testSuccessfulTerminalWaitsForIteratorCloseAndScopeCleanup(self) -> None:
        """
        Complete asynchronous iterator finalization before acknowledging success.

        Returns
        -------
        None
            Verify stream success follows both iterator and invocation-scope cleanup.
        """
        peer, manager, _task, ready = await self.connect()
        peer.input({
            "type": "invoke", "id": "close-waits", "target": "closingStream",
            "args": ["block"],
        })
        self.assertEqual((await peer.nextEnvelope())["type"], "stream_item")
        await asyncio.wait_for(self.probe.close_entered.wait(), timeout=2)
        self.assertTrue(peer.envelopes.empty())
        self.assertTrue(self.app.scopes[-1].isActive)
        self.probe.close_release.set()
        self.assertEqual(await peer.nextEnvelope(), {
            "type": "stream_complete", "id": "close-waits",
        })
        self.assertTrue(self.probe.closed_stream.is_set())
        self.assertFalse(self.app.scopes[-1].isActive)
        await self.settle(manager, ready["connection_id"])

    async def testBlockedTerminalWriteCannotBecomeADuplicateTimeout(self) -> None:
        """
        Exclude delivery of an already decided terminal from the execution deadline.

        Returns
        -------
        None
            Verify prolonged final delivery creates one successful terminal only.
        """
        peer, manager, _task, ready = await self.connect(RealtimeConfig(
            invocation_timeout=0.02,
        ))
        peer.pause_type = "completion"
        peer.write_release.clear()
        peer.input({"type": "invoke", "id": "write-waits", "target": "defaults"})
        await asyncio.wait_for(peer.write_entered.wait(), timeout=2)
        self.assertFalse(self.app.scopes[-1].isActive)
        connection = self.connection(manager, ready["connection_id"])
        self.assertEqual(connection.active, {})
        self.assertEqual(len(connection.finishing), 1)
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(peer.envelopes.get(), timeout=0.08)
        peer.write_release.set()
        self.assertEqual(await peer.nextEnvelope(), {
            "type": "completion", "id": "write-waits", "result": 7,
        })
        await self.settle(manager, ready["connection_id"])
        self.assertEqual(connection.finishing, set())
        peer.input({"type": "ping"})
        self.assertEqual(await peer.nextEnvelope(), {"type": "pong"})
        self.assertTrue(peer.envelopes.empty())

    async def testClientCanReuseIdAtTerminalBeforeSendingTaskReturns(self) -> None:
        """
        Accept reuse after delivery without letting an old callback remove new work.

        Returns
        -------
        None
            Verify immediate network-observed reuse avoids false protocol errors.
        """
        replying_peer = _ReplyingPeer()
        peer, manager, task, ready = await self.connect(peer=replying_peer)
        peer.input({
            "type": "invoke", "id": "reused", "target": "defaults", "args": [1],
        })
        self.assertEqual((await peer.nextEnvelope())["result"], 1)
        self.assertEqual((await peer.nextEnvelope())["result"], 99)
        await self.settle(manager, ready["connection_id"])
        connection = self.connection(manager, ready["connection_id"])
        self.assertEqual(connection.active, {})
        self.assertEqual(connection.finishing, set())
        self.assertTrue(replying_peer.replied)
        self.assertFalse(task.done())

    async def testCancellingStreamDuringSendPreservesSocketForOtherCalls(self) -> None:
        """
        Cancel a producer while allowing its already started frame to finish.

        Returns
        -------
        None
            Verify stream cancellation, finalization and continued RPC use.
        """
        peer, manager, _task, ready = await self.connect()
        peer.pause_type = "stream_item"
        peer.write_release.clear()
        peer.input({"type": "invoke", "id": "stream", "target": "stream", "args": [20]})
        await asyncio.wait_for(peer.write_entered.wait(), timeout=2)
        peer.input({"type": "cancel", "id": "stream"})
        await asyncio.wait_for(self.probe.closed_stream.wait(), timeout=2)
        self.assertEqual(self.probe.produced, [0])
        peer.write_release.set()
        self.assertEqual((await peer.nextEnvelope())["type"], "stream_item")
        terminal = await peer.nextEnvelope()
        self.assertEqual(terminal["type"], "stream_complete")
        self.assertEqual(terminal["error"]["code"], "cancelled")
        await self.settle(manager, ready["connection_id"])
        connection = self.connection(manager, ready["connection_id"])
        self.assertEqual(connection.active, {})
        peer.input({"type": "invoke", "id": "later", "target": "defaults"})
        self.assertEqual((await peer.nextEnvelope())["result"], 7)

    async def testImmediateCancellationClearsAdmissionAndProducesTerminal(self) -> None:
        """
        Handle cancellation queued before a new invocation task gets CPU time.

        Returns
        -------
        None
            Verify no active ID leaks when cancellation arrives in one burst.
        """
        peer, manager, _task, ready = await self.connect()
        peer.input({
            "type": "invoke", "id": "instant", "target": "gated", "args": ["x"],
        })
        peer.input({"type": "cancel", "id": "instant"})
        result = await peer.nextEnvelope()
        self.assertEqual(result["id"], "instant")
        self.assertEqual(result["error"]["code"], "cancelled")
        await self.settle(manager, ready["connection_id"])
        connection = self.connection(manager, ready["connection_id"])
        self.assertEqual(connection.active, {})
        peer.input({"type": "invoke", "id": "instant", "target": "defaults"})
        self.assertEqual((await peer.nextEnvelope())["result"], 7)

    async def testDisconnectBeforeInvocationStartsReleasesAllState(self) -> None:
        """
        Discard newly admitted work even when the peer closes in the same burst.

        Returns
        -------
        None
            Verify cleanup joins admission tasks and releases all scopes.
        """
        peer, manager, task, ready = await self.connect()
        connection = self.connection(manager, ready["connection_id"])
        peer.input({
            "type": "invoke", "id": "instant", "target": "gated", "args": ["x"],
        })
        peer.disconnect()
        await asyncio.wait_for(task, timeout=2)
        self.assertEqual(connection.active, {})
        self.assertEqual(connection.pending, {})
        self.assertEqual(manager.snapshot(), ())
        self.assertTrue(all(not scope.isActive for scope in self.app.scopes))

    async def testConcurrencyBudgetAndInvocationTimeoutRemainLocal(self) -> None:
        """
        Bound active tasks and release admission on an invocation timeout.

        Returns
        -------
        None
            Verify controlled overload and timeout replies.
        """
        peer, manager, _task, ready = await self.connect(RealtimeConfig(
            max_concurrent_invocations=1, invocation_timeout=0.05,
        ))
        peer.input({"type": "invoke", "id": "slow", "target": "gated", "args": ["x"]})
        await asyncio.wait_for(self.probe.entered.get(), timeout=2)
        peer.input({"type": "invoke", "id": "excess", "target": "defaults"})
        self.assertEqual((await peer.nextEnvelope())["error"]["code"], "busy")
        self.assertEqual((await peer.nextEnvelope())["error"]["code"], "timeout")
        await self.settle(manager, ready["connection_id"])
        connection = self.connection(manager, ready["connection_id"])
        self.assertEqual(connection.active, {})
        self.assertEqual(self.probe.settled, ["x"])

    async def testDuplicateActiveIdsAreFatalAndCleanEveryInvocation(self) -> None:
        """
        Treat ambiguous correlation reuse as a protocol violation.

        Returns
        -------
        None
            Verify protocol closure cancels existing work and group membership.
        """
        peer, manager, task, ready = await self.connect()
        connection = self.connection(manager, ready["connection_id"])
        peer.input({"type": "invoke", "id": "same", "target": "gated", "args": ["x"]})
        await asyncio.wait_for(self.probe.entered.get(), timeout=2)
        peer.input({"type": "invoke", "id": "same", "target": "defaults"})
        await asyncio.wait_for(task, timeout=2)
        self.assertEqual(peer.sent[-1]["code"], 1002)
        self.assertEqual(connection.active, {})
        self.assertEqual(manager.connectionCount, 0)
        self.assertEqual(manager.groupCount, 0)

    async def testMalformedProtocolClosesWithProtocolError(self) -> None:
        """
        Close malformed envelopes without exposing decoder implementation detail.

        Returns
        -------
        None
            Verify invalid network input triggers bounded fatal cleanup.
        """
        peer, manager, task, _ready = await self.connect()
        peer.events.put_nowait({"type": "websocket.receive", "text": "not-json"})
        await asyncio.wait_for(task, timeout=2)
        self.assertEqual(peer.sent[-1]["code"], 1002)
        self.assertEqual(manager.snapshot(), ())

    async def testMessagePackAndPingUseTheSameRuntime(self) -> None:
        """
        Select MessagePack by route while keeping identical invocation behavior.

        Returns
        -------
        None
            Verify codec-independent dispatch and application ping handling.
        """
        peer, _manager, _task, _ready = await self.connect(protocol="msgpack")
        self.assertIn("bytes", peer.sent[1])
        peer.input({"type": "ping"}, binary=True)
        self.assertEqual(await peer.nextEnvelope(), {"type": "pong"})
        peer.input({
            "type": "invoke", "id": "mp", "target": "defaults", "args": [11],
        }, binary=True)
        self.assertEqual((await peer.nextEnvelope())["result"], 11)

    async def testConnectionHookCanRejectBeforeReady(self) -> None:
        """
        Run connection authorization before accept and ready output.

        Returns
        -------
        None
            Verify rejection still releases manager and lifecycle state.
        """
        manager = ConnectionManager(RealtimeConfig())
        peer = _RealtimePeer()
        runtime = HubRuntime(cast("IApplication", self.app), manager, _RejectingHub)
        await self._serve(runtime, peer.socket())
        self.assertEqual(peer.sent, [{"type": "websocket.close", "code": 1008}])
        self.assertTrue(peer.envelopes.empty())
        self.assertEqual(manager.snapshot(), ())
        self.assertEqual(len(self.probe.disconnects), 1)

    async def testOwnerCancellationJoinsInvocationsBeforeScopeDisposal(self) -> None:
        """
        Finish active invocation finalizers before disposing connection scope.

        Returns
        -------
        None
            Verify task cancellation preserves cleanup and cancellation semantics.
        """
        peer, manager, task, ready = await self.connect()
        connection = self.connection(manager, ready["connection_id"])
        peer.input({"type": "invoke", "id": "slow", "target": "gated", "args": ["x"]})
        await asyncio.wait_for(self.probe.entered.get(), timeout=2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.probe.settled, ["x"])
        self.assertEqual(connection.active, {})
        self.assertEqual(manager.snapshot(), ())
        self.assertTrue(all(not scope.isActive for scope in self.app.scopes))
