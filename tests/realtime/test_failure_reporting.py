# ruff: noqa: ANN001, ANN201, ANN202, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify central delivery across Hub invocations, broadcasts and cleanup."""

import asyncio
from functools import partial
from types import SimpleNamespace
import msgspec
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context
from orionis.container.container import Container
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.runtime import FailureRuntime, capture, operation
from orionis.http.exceptions.websocket import WebSocketDisconnected
from orionis.realtime.config import RealtimeConfig
from orionis.realtime.connection import RealtimeConnection
from orionis.realtime.decorators import remote
from orionis.realtime.entities import BroadcastResult
from orionis.realtime.errors import RPCError
from orionis.realtime.hub import Hub, HubContext
from orionis.realtime.manager import ConnectionManager
from orionis.realtime.protocol import HubProtocol
from orionis.realtime.runtime import HubRuntime
from tests.support.failure_runtime import IsolatedFailureTestCase
from tests.realtime.test_connection import _RealtimePeer
from tests.realtime.test_manager import _Connection


class _FailureContainer(Container):
    """Isolate runtime ownership from other test applications."""


class _Handler:
    """Collect native handler deliveries without replacing the coordinator."""

    def __init__(self) -> None:
        self.events = []
        self.reports = []
        self.results = []

    async def handleFailure(self, exception, context) -> FailureHandling:
        self.events.append((exception, context))

        async def log() -> None:
            self.reports.append(exception)

        return FailureHandling(
            logging=log if not context.expected and context.reporting_allowed else None,
        )

    async def handleResult(self, value, context) -> None:
        self.results.append((value, context))


class _State:
    def __init__(self) -> None:
        self.failures = {}
        self.disconnect_error = None


class _ReportingHub(Hub):
    def __init__(self, state: _State) -> None:
        self.state = state

    @remote
    async def fail(self, identifier: str) -> str:
        raise self.state.failures[identifier]

    @remote
    async def echo(self, value: str) -> str:
        return value

    async def onDisconnect(self, code: int, reason: str) -> None:
        del code, reason
        if self.state.disconnect_error is not None:
            raise self.state.disconnect_error


class TestRealtimeFailureReporting(IsolatedFailureTestCase):
    """Require original errors without changing wire messages or ownership."""

    async def asyncSetUp(self) -> None:
        """Prepare an isolated active app with a real recording handler."""
        self.app = _FailureContainer()
        self.handler = _Handler()
        self.runtime = FailureRuntime(self.app, self.handler)
        self.app._failure_runtime = self.runtime
        self.owner = object()
        self.runtime.activate(self.owner)
        self.state = _State()
        self.app.instance(_State, self.state)
        self.tasks = []

    async def asyncTearDown(self) -> None:
        """Join test connections and release application runtime ownership."""
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.runtime.drain()
        self.runtime.deactivate(self.owner)
        Container._instances.pop(_FailureContainer, None)

    async def testFinalizationPreservesPrimaryAcrossCleanupAndCloseFailures(
        self,
    ) -> None:
        """Finish disconnect while retaining the escaping error or cancellation."""
        for original in (None, ValueError("primary"), asyncio.CancelledError()):
            for closing_error in (None, RuntimeError("close")):
                with self.subTest(original=original, closing=closing_error):
                    self.handler.events.clear()
                    cause = LookupError("original cause")
                    if original is not None:
                        original.__cause__ = cause
                    cleanup_error = OSError("cleanup")
                    order = []

                    async def cleanup(
                        error: OSError = cleanup_error,
                        order: list = order,
                    ) -> None:
                        """Fail before the connection is unregistered."""
                        order.append("cleanup")
                        raise error

                    async def disconnect(
                        _connection: object,
                        _code: int,
                        _reason: str,
                        error: RuntimeError | None = closing_error,
                        order: list = order,
                    ) -> None:
                        """Attempt socket closure even when owned cleanup failed."""
                        order.append("disconnect")
                        if error is not None:
                            raise error

                    connection = SimpleNamespace(
                        cleanup=cleanup,
                        context=SimpleNamespace(connection_id="test"),
                    )
                    runtime = SimpleNamespace(
                        _app=self.app,
                        _disconnect=disconnect,
                        _manager=SimpleNamespace(
                            unregister=lambda _connection, order=order: order.append(
                                "unregister",
                            ),
                        ),
                    )
                    expected = original if original is not None else cleanup_error
                    with (
                        operation(self.app, flow="realtime", isolated=True),
                        self.assertRaises(type(expected)) as caught,
                    ):
                        await HubRuntime._finishConnection(
                            runtime,
                            connection,
                            1000,
                            "",
                            original,
                        )
                    self.assertIs(caught.exception, expected)
                    if original is not None:
                        self.assertIs(original.__cause__, cause)
                    self.assertEqual(order, ["cleanup", "unregister", "disconnect"])
                    failures = [cleanup_error]
                    if closing_error is not None:
                        failures.append(closing_error)
                    self.assertEqual(
                        [error for error, _ in self.handler.events],
                        failures,
                    )

    async def connect(self):
        """Start an authenticated connection through the actual Hub runtime."""
        manager = ConnectionManager(RealtimeConfig())
        peer = _RealtimePeer()
        hub = HubRuntime(self.app, manager, _ReportingHub)

        async def serve():
            async with self.app.beginScope():
                bind_auth_context(AuthenticationContext())
                await hub.serve(peer.socket())

        task = asyncio.create_task(serve())
        self.tasks.append(task)
        ready = await peer.nextEnvelope()
        self.assertEqual(ready["type"], "ready")
        return peer, manager, task

    async def testConcurrentInvocationFailuresKeepIdsAndConnection(self) -> None:
        """Report independent failures while preserving request correlation."""
        self.state.failures = {
            "first": ValueError("private-first"),
            "second": OSError("private-second"),
        }
        peer, manager, task = await self.connect()
        for identifier in self.state.failures:
            peer.input(
                {
                    "type": "invoke",
                    "id": identifier,
                    "target": "fail",
                    "args": [identifier],
                },
            )
        replies = [await peer.nextEnvelope(), await peer.nextEnvelope()]
        self.assertCountEqual([reply["id"] for reply in replies], ["first", "second"])
        self.assertNotIn("private-", str(replies))
        self.assertEqual(manager.connectionCount, 1)
        self.assertCountEqual(
            [error for error, _ in self.handler.events],
            list(self.state.failures.values()),
        )
        self.assertCountEqual(
            [context.correlation_id for _, context in self.handler.events],
            ["first", "second"],
        )
        peer.disconnect()
        await task

    async def testExpectedInvocationFailureIsObservedWithoutServerLog(self) -> None:
        """Keep controlled RPC failures out of unexpected-error logging."""
        error = RPCError("conflict", "private-domain-detail")
        self.state.failures["expected"] = error
        peer, _, task = await self.connect()
        peer.input(
            {
                "type": "invoke",
                "id": "expected",
                "target": "fail",
                "args": ["expected"],
            },
        )
        reply = await peer.nextEnvelope()
        self.assertEqual(reply["error"]["code"], "conflict")
        self.assertIs(self.handler.events[0][0], error)
        self.assertTrue(self.handler.events[0][1].expected)
        self.assertEqual(self.handler.reports, [])
        peer.disconnect()
        await task

    async def testDisconnectHookFailureDoesNotPreventConnectionCleanup(self) -> None:
        """Observe a failed disconnect hook after unregistering the connection."""
        error = ValueError("disconnect-hook")
        self.state.disconnect_error = error
        peer, manager, task = await self.connect()
        peer.disconnect()
        await task
        self.assertEqual(manager.connectionCount, 0)
        self.assertEqual([event[0] for event in self.handler.events], [error])
        self.assertEqual(self.handler.events[0][1].phase, "disconnect_hook")

    async def testBroadcastFailurePreservesOtherRecipients(self) -> None:
        """Observe one failed send without changing successful recipients."""
        manager = ConnectionManager(RealtimeConfig())
        healthy = _Connection("healthy", hub=_ReportingHub)
        broken = _Connection("broken", hub=_ReportingHub)
        broken.fail = True
        manager.register(healthy)
        manager.register(broken)
        with operation(self.app, flow="realtime", operation="broadcast"):
            result = await manager.broadcast(
                _ReportingHub,
                ("healthy", "broken"),
                {"type": "notice"},
            )
        self.assertEqual(result, BroadcastResult(sent=1, failed=1))
        self.assertEqual(len(healthy.sent), 1)
        self.assertEqual(len(self.handler.events), 1)
        self.assertEqual(self.handler.events[0][1].correlation_id, "broken")

    async def testCleanupObservesAllConcurrentFinallyFailuresOnce(self) -> None:
        """Deliver every child failure even when all fail during cancellation."""
        peer = _RealtimePeer()
        connection = RealtimeConnection(
            HubContext(connection_id="cleanup", socket=peer.socket()),
            _ReportingHub,
            HubProtocol(),
            RealtimeConfig(),
            runtime=self.runtime,
        )
        ready = asyncio.Queue()

        async def child(identifier):
            ready.put_nowait(identifier)
            try:
                await asyncio.Event().wait()
            finally:
                raise RuntimeError(identifier)

        with operation(self.app, flow="realtime", operation="cleanup"):
            for identifier in ("first-cleanup", "second-cleanup"):
                task = asyncio.create_task(child(identifier))
                connection.active[identifier] = task
                task.add_done_callback(partial(connection.invocationDone, identifier))
            await ready.get()
            await ready.get()
            await connection.cleanup()
        self.assertCountEqual(
            [str(error) for error, _ in self.handler.events],
            ["first-cleanup", "second-cleanup"],
        )
        self.assertEqual(connection.active, {})
        self.assertIsNone(connection.owner)

    async def testRejectedInvocationProducesResultWithoutFakeException(self) -> None:
        """Represent admission failures using the structured result hook."""
        peer, _, task = await self.connect()
        peer.input({"type": "invoke", "id": "missing", "target": "missing"})
        reply = await peer.nextEnvelope()
        self.assertEqual(reply["error"]["code"], "method_not_found")
        self.assertEqual(self.handler.events, [])
        self.assertEqual(self.handler.results[0][0], "method_not_found")
        peer.disconnect()
        await task

    async def testFatalWriteHandoffDoesNotDuplicateAtConnectionOwner(self) -> None:
        """Transfer a fatal child write's receipt before waking its owner."""
        error = OSError("transport-send")

        class Peer(_RealtimePeer):
            async def send(self, event: dict) -> None:
                if event["type"] == "websocket.send":
                    envelope = msgspec.json.decode(event["text"])
                    if envelope["type"] == "completion":
                        raise error
                await super().send(event)

        peer = Peer()
        manager = ConnectionManager(RealtimeConfig())
        hub = HubRuntime(self.app, manager, _ReportingHub)

        async def serve():
            async with self.app.beginScope():
                bind_auth_context(AuthenticationContext())
                with operation(self.app, flow="http"):
                    try:
                        await hub.serve(peer.socket())
                    except Exception as exc:
                        await capture(exc, app=self.app, flow="http")
                        raise

        task = asyncio.create_task(serve())
        self.tasks.append(task)
        await peer.nextEnvelope()
        peer.input({"type": "invoke", "id": "echo", "target": "echo", "args": ["ok"]})
        with self.assertRaises(WebSocketDisconnected) as caught:
            await task
        self.assertIs(caught.exception.__cause__, error)
        self.assertEqual([event[0] for event in self.handler.events], [error])
        self.assertEqual(manager.connectionCount, 0)

    async def testLateCallbackTransfersFromAnAlreadyClosedInvocation(self) -> None:
        """Deduplicate a late shielded write after its invocation scope exits."""
        error = OSError("late-send")
        wrapper = WebSocketDisconnected()
        wrapper.__cause__ = error
        peer = _RealtimePeer()
        with operation(self.app, flow="http"):
            connection = RealtimeConnection(
                HubContext(connection_id="late", socket=peer.socket()),
                _ReportingHub,
                HubProtocol(),
                RealtimeConfig(),
                runtime=self.runtime,
            )
            with operation(self.app, flow="realtime", isolated=True):
                asyncio.get_running_loop().call_soon(
                    connection._observe,
                    wrapper,
                    "send",
                )
            await asyncio.sleep(0)
            await capture(wrapper, app=self.app, flow="http")
            await self.runtime.drain()
        self.assertEqual([event[0] for event in self.handler.events], [error])

    async def testShieldedWriteFailureOutlivesCancelledInvocation(self) -> None:
        """Keep one incident when an actual transport write outlives its caller."""
        error = OSError("late-shielded-send")
        started, release = asyncio.Event(), asyncio.Event()

        class Peer(_RealtimePeer):
            async def send(self, event: dict) -> None:
                if event["type"] == "websocket.send":
                    started.set()
                    await release.wait()
                    raise error
                await super().send(event)

        with operation(self.app, flow="http"):
            socket = Peer().socket()
            await socket.accept()
            connection = RealtimeConnection(
                HubContext(connection_id="shielded", socket=socket),
                _ReportingHub,
                HubProtocol(),
                RealtimeConfig(),
                runtime=self.runtime,
            )
            connection.owner = None

            async def invoke():
                with operation(self.app, flow="realtime", isolated=True):
                    await connection.sendEncoded("{}")

            caller = asyncio.create_task(invoke())
            await started.wait()
            write = connection._write_task
            caller.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await caller
            release.set()
            await asyncio.gather(write, return_exceptions=True)
            await capture(connection.failure, app=self.app, flow="http")
            await connection.cleanup()
            await self.runtime.drain()
        self.assertEqual([event[0] for event in self.handler.events], [error])
