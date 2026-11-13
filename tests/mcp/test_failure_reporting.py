# ruff: noqa: ANN001, ANN202, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise central failure delivery through real MCP execution boundaries."""

import asyncio
from contextlib import suppress
from functools import partial
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from orionis.container.container import Container
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.runtime import FailureRuntime, operation
from orionis.http.responses import HTMLResponse
from orionis.mcp.config import McpConfig
from orionis.mcp.protocol.results import CallToolResult
from orionis.mcp.reporting import report
from orionis.mcp.server.primitives import Resource, Server, Tool
from orionis.mcp.streams import OwnedStream
from orionis.mcp.transport.http import McpHttpTransport, _EventFrames
from orionis.mcp.transport.policy import McpHttpPolicy
from orionis.mcp.transport.stdio import McpStdioTransport
from orionis.mcp.transport.standard_io import StandardReader, _finish_write
from orionis.test import TestCase
from orionis.test.clients.mcp import McpTestClient
from tests.mcp.transport.test_stdio import _Reader, _Writer
from tests.mcp.test_streams import _Source


class _FailureContainer(Container):
    """Keep test runtime registration separate from application services."""


class _Handler:
    """Observe the original errors and the unmodified contextual hook contract."""

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


class _BrokenTool(Tool):
    name = "broken"

    async def handle(self):
        message = "private-tool-detail"
        raise ValueError(message)


class _DeclaredFailure(Tool):
    name = "declared"

    async def handle(self):
        return CallToolResult(content=(), isError=True)


class _GroupedFailure(Tool):
    name = "grouped"

    async def handle(self):
        message = "mixed-control-flow"
        raise BaseExceptionGroup(message, [ValueError(), asyncio.CancelledError()])


class _BrokenResource(Resource):
    name = "broken-resource"
    uri = "memory://broken"

    async def handle(self):
        message = "private-resource-detail"
        raise OSError(message)


class _Server(Server):
    name = "Failure delivery"
    tools = (_BrokenTool, _DeclaredFailure, _GroupedFailure)
    resources = (_BrokenResource,)


class _NoDispatchStdio(McpStdioTransport):
    """Reach the real EOF drain with deterministic failing child cleanup."""

    async def _readLoop(self, reader, writer) -> None:
        del reader, writer
        ready = asyncio.Queue()

        async def child(label):
            ready.put_nowait(label)
            try:
                await asyncio.Event().wait()
            finally:
                raise RuntimeError(label)

        for label in ("first-cleanup", "second-cleanup"):
            task = asyncio.create_task(child(label))
            self._active[label] = task
            task.add_done_callback(partial(self._done, label))
        await ready.get()
        await ready.get()


class TestMcpFailureReporting(TestCase):
    """Keep public protocol results stable while delivering every failure."""

    async def asyncSetUp(self) -> None:
        """Activate a runtime with real container dispatch and a recording handler."""
        self.app = _FailureContainer()
        self.handler = _Handler()
        self.runtime = FailureRuntime(self.app, self.handler)
        self.app._failure_runtime = self.runtime
        self.owner = object()
        self.runtime.activate(self.owner)
        self.client = McpTestClient(self.app, _Server)

    async def asyncTearDown(self) -> None:
        """Drain owned reporting and remove the isolated container instance."""
        await self.runtime.drain()
        self.runtime.deactivate(self.owner)
        Container._instances.pop(_FailureContainer, None)

    async def testEmbeddedContainerPreventsRecursiveLogging(self) -> None:
        """Use the runtime guard when a standalone embedder logs another error."""
        primary = ValueError("private primary")
        secondary = OSError("private secondary")
        events = []
        logs = []

        async def log() -> None:
            logs.append(primary)
            await report(secondary, embedder)

        async def handle_failure(exception, context) -> FailureHandling:
            events.append((exception, context))
            return FailureHandling(logging=log)

        async def get_handler():
            return SimpleNamespace(handleFailure=handle_failure)

        embedder = SimpleNamespace(
            call=self.app.call,
            getExceptionHandler=get_handler,
        )
        diagnostic = StringIO()
        with patch("sys.stderr", diagnostic):
            await report(primary, embedder)
        self.assertEqual([error for error, _ in events], [primary])
        self.assertEqual(logs, [primary])
        self.assertEqual(events[0][1].flow, "mcp")
        self.assertIsNotNone(events[0][1].event_id)
        self.assertNotIn("private", diagnostic.getvalue())
        self.assertIn("OSError", diagnostic.getvalue())

    async def testToolFailureReachesHandlerWithoutLeakingIntoProtocol(self) -> None:
        """Observe the tool's original exception and preserve sanitized results."""
        response = await self.client.tool("broken")
        self.assertTrue(response.message["result"]["isError"])
        self.assertNotIn("private-tool-detail", str(response.message))
        self.assertEqual(len(self.handler.events), 1)
        error, context = self.handler.events[0]
        self.assertIs(type(error), ValueError)
        self.assertIs(self.handler.reports[0], error)
        self.assertEqual((context.flow, context.operation), ("mcp", "tools/call"))

    async def testTranslatedResourceFailureReportsOriginalOnce(self) -> None:
        """Deduplicate a resource error across its protocol translation."""
        response = await self.client.request(
            "resources/read",
            {"uri": "memory://broken"},
        )
        self.assertEqual(response.message["error"]["code"], -32603)
        self.assertEqual(len(self.handler.events), 1)
        self.assertIs(type(self.handler.events[0][0]), OSError)

    async def testDeclaredToolFailureIsAResultWithoutFakeException(self) -> None:
        """Deliver explicit isError results through the result hook only."""
        response = await self.client.tool("declared")
        self.assertTrue(response.message["result"]["isError"])
        self.assertEqual(self.handler.events, [])
        self.assertEqual(self.handler.reports, [])
        self.assertEqual(self.handler.results[0][0], "tool_error")

    async def testExpectedProtocolFailureIsObservedWithoutErrorLog(self) -> None:
        """Classify client mistakes without logging a server error."""
        response = await self.client.request("tools/call", {"name": "absent"})
        self.assertIn("error", response.message)
        self.assertEqual(len(self.handler.events), 1)
        self.assertTrue(self.handler.events[0][1].expected)
        self.assertEqual(self.handler.reports, [])

    async def testHttpTransportConsumesFailureOnlyAfterReportingOriginal(self) -> None:
        """Observe a transport failure before returning a sanitized response."""
        transport = object.__new__(McpHttpTransport)
        transport._app = self.app
        transport._active = 0
        transport._origins = frozenset()
        request = SimpleNamespace(method="POST", headers=None)
        response = await transport.handle(request)
        self.assertEqual(response.getStatusCode(), 500)
        self.assertEqual(len(self.handler.events), 1)
        self.assertEqual(self.handler.events[0][1].phase, "request")
        self.assertNotIn("AttributeError", response.getBody().decode())

    async def testResponseCleanupPreservesCancellationAndOrdinaryPrimary(self) -> None:
        """Never replace cleanup cancellation with a response construction error."""
        transport = object.__new__(McpHttpTransport)
        transport._app = self.app
        cases = (
            (ValueError("response"), OSError("cleanup"), False),
            (ValueError("response"), asyncio.CancelledError(), True),
            (asyncio.CancelledError(), OSError("cleanup"), False),
        )
        for original, cleanup, use_cleanup in cases:
            with self.subTest(original=type(original), cleanup=type(cleanup)):
                events = SimpleNamespace(aclose=AsyncMock(side_effect=cleanup))
                expected = cleanup if use_cleanup else original
                with (
                    patch(
                        "orionis.mcp.transport.http.EventStreamResponse",
                        side_effect=original,
                    ),
                    self.assertRaises(type(expected)) as caught,
                ):
                    await transport._streamResponse(events, 200)
                self.assertIs(caught.exception, expected)
                events.aclose.assert_awaited_once()

    async def testStreamCleanupDistinguishesCallerAndInternalCancellation(self) -> None:
        """
        Drain cleanup while preserving real caller cancellation and primary errors.

        Returns
        -------
        None
            Observe the original once and never turn internal cancellation into
            caller cancellation, including an earlier consumed cancellation.
        """
        for mode in ("caller", "internal", "consumed", "pending"):
            with self.subTest(mode=mode):
                self.handler.events.clear()
                self.handler.reports.clear()
                original = ValueError("producer")
                source = _Source()
                source.release.clear()
                if mode in ("internal", "consumed"):
                    source.aclose = AsyncMock(side_effect=asyncio.CancelledError())
                elif mode == "pending":
                    source.release.set()

                async def consume(source: _Source, mode: str) -> None:
                    """
                    Start an independent stream operation after optional cancellation.

                    Parameters
                    ----------
                    source : _Source
                        Producer with controlled cleanup.
                    mode : str
                        Cancellation scenario owned by this task.

                    Returns
                    -------
                    None
                        Propagate the owned stream outcome to the caller.
                    """
                    if mode in ("consumed", "pending"):
                        asyncio.current_task().cancel()
                    if mode == "consumed":
                        with suppress(asyncio.CancelledError):
                            await asyncio.sleep(0)
                    with operation(self.app, flow="mcp", isolated=True):
                        await anext(OwnedStream(source))

                with patch.object(
                    _Source,
                    "__anext__",
                    AsyncMock(side_effect=original),
                ) as read:
                    owner = asyncio.create_task(consume(source, mode))
                    if mode == "caller":
                        await source.closing.wait()
                        owner.cancel()
                        source.release.set()
                    expected = (
                        asyncio.CancelledError
                        if mode in ("caller", "pending")
                        else ValueError
                    )
                    with self.assertRaises(expected) as caught:
                        await owner
                self.assertEqual(owner.cancelled(), mode in ("caller", "pending"))
                if mode in ("caller", "pending"):
                    self.assertEqual(source.closes, 1)
                else:
                    self.assertIs(caught.exception, original)
                    source.aclose.assert_awaited_once()
                errors = [] if mode == "pending" else [original]
                self.assertEqual([error for error, _ in self.handler.events], errors)
                self.assertEqual(self.handler.reports, errors)
                if mode == "pending":
                    read.assert_not_awaited()
                else:
                    self.assertEqual(self.handler.events[0][1].phase, "stream")

    async def testCancelledResponseReportingReleasesAdmission(self) -> None:
        """Release the stream slot when cancellation interrupts the app handler."""
        transport = object.__new__(McpHttpTransport)
        transport._app = self.app
        transport._active = 1
        source = SimpleNamespace(aclose=AsyncMock())
        events = _EventFrames(source, transport._release)
        entered = asyncio.Event()

        async def stalled(_handler, exception, context):
            del exception, context
            entered.set()
            await asyncio.Event().wait()

        with (
            patch(
                "orionis.mcp.transport.http.EventStreamResponse",
                side_effect=ValueError("response"),
            ),
            patch.object(_Handler, "handleFailure", stalled),
        ):
            task = asyncio.create_task(transport._streamResponse(events, 200))
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        source.aclose.assert_awaited_once()
        self.assertEqual(transport._active, 0)

    async def testStdioEofObservesBothCleanupFailuresWithoutOutput(self) -> None:
        """Inspect every drained task when input ends with active requests."""
        transport = _NoDispatchStdio(
            self.app,
            self.client.dispatcher.server,
            McpConfig(),
            self.client.dispatcher.bus,
        )
        await transport.run(None, None)
        await self.runtime.drain()
        self.assertCountEqual(
            [str(error) for error, _ in self.handler.events],
            ["first-cleanup", "second-cleanup"],
        )
        self.assertEqual(transport._active, {})
        self.assertFalse(transport._running)

    async def testStreamPreservesPrimaryAndObservesCleanup(self) -> None:
        """Keep the producer exception when finalizing the source also fails."""
        for chaining in ("explicit", "implicit", "suppressed"):
            with self.subTest(chaining=chaining):
                self.handler.events.clear()
                primary = ValueError("producer")
                cause = LookupError("original producer cause")
                primary.__context__ = cause
                if chaining == "explicit":
                    primary.__cause__ = cause
                elif chaining == "suppressed":
                    primary.__suppress_context__ = True
                chain = (
                    primary.__cause__,
                    primary.__context__,
                    primary.__suppress_context__,
                )
                secondary = OSError("cleanup")

                class Source:
                    def __aiter__(self) -> Source:
                        return self

                    async def __anext__(self, error=primary) -> object:
                        raise error

                    async def aclose(self, error=secondary):
                        raise error

                with (
                    operation(self.app, flow="mcp"),
                    self.assertRaises(ValueError) as caught,
                ):
                    await anext(OwnedStream(Source()))
                self.assertIs(caught.exception, primary)
                self.assertEqual(
                    (
                        primary.__cause__,
                        primary.__context__,
                        primary.__suppress_context__,
                    ),
                    chain,
                )
                self.assertEqual(
                    [error for error, _ in self.handler.events],
                    [primary, secondary],
                )
                self.assertEqual(
                    self.handler.events[1][1].parent_event_id,
                    self.handler.events[0][1].event_id,
                )

    async def testInactiveRuntimeDoesNotReportNewFailures(self) -> None:
        """Exclude the interval before successful startup and after shutdown."""
        self.runtime.deactivate(self.owner)
        response = await self.client.tool("broken")
        self.assertTrue(response.message["result"]["isError"])
        self.assertEqual(self.handler.events, [])
        self.assertEqual(self.handler.reports, [])

    async def testCancelledWriterStillReportsItsLateIoFailure(self) -> None:
        """Observe an OS write error after its original waiter was cancelled."""
        error = BrokenPipeError("late-write")
        future = asyncio.get_running_loop().create_future()
        future.cancel()
        with operation(self.app, flow="mcp", operation="stdio"):
            _finish_write(future, error, self.runtime)
            await self.runtime.drain()
        self.assertTrue(future.cancelled())
        self.assertEqual([event[0] for event in self.handler.events], [error])

    async def testMixedExceptionGroupKeepsIdentityAndPropagates(self) -> None:
        """Observe a mixed group without sanitizing away cancellation members."""
        with self.assertRaises(BaseExceptionGroup) as caught:
            await self.client.tool("grouped")
        self.assertEqual(
            [event[0] for event in self.handler.events],
            [caught.exception],
        )
        self.assertIsInstance(caught.exception.exceptions[1], asyncio.CancelledError)

    async def testStdioFramingReportsBeforeReturningOriginalWireError(self) -> None:
        """Observe malformed input while preserving the JSON-RPC parse response."""
        reader, writer = _Reader(), _Writer()
        transport = McpStdioTransport(
            self.app,
            self.client.dispatcher.server,
            McpConfig(),
            self.client.dispatcher.bus,
        )
        task = asyncio.create_task(transport.run(reader, writer))
        reader.queue.put_nowait(b"{invalid}\n")
        try:
            async with asyncio.timeout(2):
                response = await writer.queue.get()
            self.assertEqual(response["error"]["code"], -32700)
            self.assertEqual(len(self.handler.events), 1)
            self.assertTrue(self.handler.events[0][1].expected)
            self.assertEqual(self.handler.reports, [])
        finally:
            reader.queue.put_nowait(b"")
            await task

    async def testMalformedCancellationRemainsSilentAndObserved(self) -> None:
        """Keep cancellation notifications response-free even when malformed."""
        reader, writer = _Reader(), _Writer()
        transport = McpStdioTransport(
            self.app,
            self.client.dispatcher.server,
            McpConfig(),
            self.client.dispatcher.bus,
        )
        reader.queue.put_nowait(
            b'{"jsonrpc":"2.0","method":"notifications/cancelled",'
            b'"params":{"requestId":[]}}\n',
        )
        reader.queue.put_nowait(b"")
        await transport.run(reader, writer)
        self.assertEqual(writer.writes, [])
        self.assertEqual(len(self.handler.events), 1)
        self.assertTrue(self.handler.events[0][1].expected)

    async def testHttpPolicyReportsRejectedHtmlAsResult(self) -> None:
        """Observe an invalid protocol response without manufacturing an error."""
        policy = McpHttpPolicy(self.app, McpConfig())
        response = await policy.response(HTMLResponse("Unexpected browser body"))
        self.assertEqual(response.getStatusCode(), 403)
        self.assertEqual(self.handler.events, [])
        self.assertEqual(self.handler.results[0][0], "response_rejected")

    async def testClosingReaderObservesAnUnreadThreadFailure(self) -> None:
        """Retain a daemon error even if shutdown wins before the next read."""
        error = ValueError("unread-stdin")

        class BrokenInput:
            def readline(self, limit):
                del limit
                raise error

        reader = StandardReader(BrokenInput(), 128, runtime=self.runtime)
        try:
            async with asyncio.timeout(2):
                # Observe queue admission without transferring it to readline().
                self.assertIs(await reader._queue.get(), error)
        finally:
            reader.close()
        await self.runtime.drain()
        self.assertEqual([event[0] for event in self.handler.events], [error])

    async def testInternalProtocolFailureRemainsAnUnexpectedError(self) -> None:
        """Keep server response failures distinct from expected client mistakes."""
        client = McpTestClient(self.app, _Server, McpConfig(max_response_size=1))
        response = await client.request("tools/list")
        self.assertEqual(response.message["error"]["code"], -32603)
        self.assertEqual(len(self.handler.events), 1)
        error, context = self.handler.events[0]
        self.assertFalse(context.expected)
        self.assertEqual(self.handler.reports, [error])
