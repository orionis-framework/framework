# ruff: noqa: ANN001, ANN201, ANN202, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import asyncio
import inspect
import io
import msgspec
from orionis.container.container import Container
from orionis.container.context.scope import get_current_scope
from orionis.mcp.config import McpConfig
from orionis.mcp.dispatcher import DispatchResult
from orionis.mcp.protocol.codecs import decode_params
from orionis.mcp.protocol.constants import CLIENT_CAPABILITIES, PROTOCOL_VERSION
from orionis.mcp.transport import stdio as module
from orionis.mcp.transport.standard_io import StandardReader, StandardWriter
from orionis.mcp.transport.stdio import McpStdioTransport
from orionis.test import TestCase


class _Reader:
    """Permit independently scheduled requests, cancellation and EOF."""

    __slots__ = ("queue",)

    def __init__(self) -> None:
        """Create an input queue controlled by the current test.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.queue = asyncio.Queue()

    async def readline(self):
        """Wait for one frame without blocking the request tasks.

        Returns
        -------
        object
            Return the result produced by ``readline``.
        """
        return await self.queue.get()


class _Writer:
    """Capture indivisible output frames and optionally simulate a broken pipe."""

    __slots__ = ("broken", "queue", "writes")

    def __init__(self) -> None:
        """Create observation state and a healthy transport.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.queue = asyncio.Queue()
        self.writes = []
        self.broken = False

    async def write(self, data):
        """Record exactly one write or fail as a closed output pipe would.

        Parameters
        ----------
        data : object
            Value supplied for ``data``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        if self.broken:
            message = "closed pipe"
            raise BrokenPipeError(message)
        self.writes.append(data)
        await self.queue.put(msgspec.json.decode(data))


class _ShortOutput(io.BytesIO):
    """Simulate a raw pipe that accepts only part of each write."""

    def __init__(self, limit: int | None) -> None:
        """Store the maximum accepted bytes per call.

        Parameters
        ----------
        limit : int | None
            Positive partial-write size, or a zero-progress result.

        Returns
        -------
        None
            No return value.
        """
        super().__init__()
        self.limit = limit
        self.flushes = 0

    def write(self, data):
        """Write only the accepted prefix or report no progress.

        Parameters
        ----------
        data : object
            Bytes offered by the writer daemon.

        Returns
        -------
        int | None
            Number of accepted bytes, or None when blocked.
        """
        if self.limit in (None, 0):
            return self.limit
        return super().write(data[: self.limit])

    def flush(self) -> None:
        """Record completed-frame flushes.

        Returns
        -------
        None
            No return value.
        """
        self.flushes += 1
        super().flush()


class _App:
    """Own real container scopes and deterministic dispatch lifecycle observations."""

    __slots__ = ("cancelled", "container", "gates", "scopes", "started")

    def __init__(self) -> None:
        """Initialize an application double with the real Orionis container.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.container = Container()
        self.gates = {}
        self.scopes = {}
        self.started = asyncio.Queue()
        self.cancelled = asyncio.Queue()

    def beginScope(self):
        """Open a fresh contextvars-backed request scope.

        Returns
        -------
        object
            Return the result produced by ``beginScope``.
        """
        return self.container.beginScope()


class _Dispatcher:
    """Observe concurrency without involving primitive-specific behavior."""

    __slots__ = ("app",)

    def __init__(self, app, _compiled, _config, _bus) -> None:
        """Share explicit test controls across independent invocations.

        Parameters
        ----------
        app : object
            Value supplied for ``app``.
        _compiled : object
            Value supplied for ``_compiled``.
        _config : object
            Value supplied for ``_config``.
        _bus : object
            Value supplied for ``_bus``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.app = app

    def decode(self, request):
        """Retain real protocol metadata and method decoding.

        Parameters
        ----------
        request : object
            Value supplied for ``request``.

        Returns
        -------
        object
            Return the result produced by ``decode``.
        """
        return decode_params(request)

    async def dispatch(self, request, _params, **_options: object):
        """Wait only when requested and record the active invocation scope.

        Parameters
        ----------
        request : object
            Value supplied for ``request``.
        _params : object
            Value supplied for ``_params``.
        **_options : object
            Value supplied for ``_options``.

        Returns
        -------
        DispatchResult
            Return the result produced by ``dispatch``.
        """
        self.app.scopes[request.id] = get_current_scope()
        self.app.started.put_nowait(request.id)
        try:
            gate = self.app.gates.get(request.id)
            if gate is not None:
                await gate.wait()
        except asyncio.CancelledError:
            self.app.cancelled.put_nowait(request.id)
            raise
        return DispatchResult(
            msgspec.json.encode(
                {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "result": {"resultType": "complete"},
                },
            ),
        )


class TestStdioTransport(TestCase):
    """Keep cancellation independent of running tools and unrelated calls."""

    def setUp(self):
        """Replace the dispatcher boundary with an explicit deterministic double.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.original = module.McpDispatcher
        module.McpDispatcher = _Dispatcher
        self.app = _App()
        self.reader = _Reader()
        self.writer = _Writer()

    def tearDown(self):
        """Restore the shared dispatcher module for other suites.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        module.McpDispatcher = self.original

    def frame(self, request_id=1, method="server/discover"):
        """Encode one complete request with the mandatory modern metadata.

        Parameters
        ----------
        request_id : object
            Value supplied for ``request_id``.
        method : object
            Value supplied for ``method``.

        Returns
        -------
        object
            Return the result produced by ``frame``.
        """
        return (
            msgspec.json.encode(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": {
                        "_meta": {
                            PROTOCOL_VERSION: "2026-07-28",
                            CLIENT_CAPABILITIES: {},
                        },
                    },
                },
            )
            + b"\n"
        )

    def transport(self, **options: object):
        """Construct a bounded transport using the real configuration validation.

        Parameters
        ----------
        **options : object
            Value supplied for ``options``.

        Returns
        -------
        McpStdioTransport
            Return the result produced by ``transport``.
        """
        return McpStdioTransport(self.app, None, McpConfig(**options), None)

    async def finish(self, running):
        """End input and require prompt task cleanup.

        Parameters
        ----------
        running : object
            Value supplied for ``running``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        await self.reader.queue.put(b"")
        await asyncio.wait_for(running, 1)

    async def testConcurrentCallsHaveIndependentScopesAndFraming(self):
        """A blocked first call does not delay a second response or share its scope.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.app.gates[1] = asyncio.Event()
        transport = self.transport()
        running = asyncio.create_task(transport.run(self.reader, self.writer))
        await self.reader.queue.put(self.frame(1))
        self.assertEqual(await self.app.started.get(), 1)
        await self.reader.queue.put(self.frame(2))
        self.assertEqual((await asyncio.wait_for(self.writer.queue.get(), 1))["id"], 2)
        self.assertIsNot(self.app.scopes[1], self.app.scopes[2])
        self.app.gates[1].set()
        self.assertEqual((await asyncio.wait_for(self.writer.queue.get(), 1))["id"], 1)
        await self.finish(running)
        self.assertTrue(all(not scope.isActive for scope in self.app.scopes.values()))
        self.assertTrue(all(frame.count(b"\n") == 1 for frame in self.writer.writes))
        self.assertEqual(transport._active, {})

    async def testRejectedRequestTaskClosesItsCoroutineWithoutAdmission(self) -> None:
        """Do not leak an unstarted invocation when the task factory rejects it.

        Returns
        -------
        None
            No return value.
        """
        transport = self.transport()
        loop = asyncio.get_running_loop()
        factory = loop.get_task_factory()
        rejected = []
        failure = RuntimeError("Request task rejected")

        def reject(_loop, coroutine, **_kwargs: object):
            """Record the unscheduled coroutine and reject its admission.

            Parameters
            ----------
            _loop : object
                Current event loop.
            coroutine : object
                Coroutine offered to the factory.
            **_kwargs : object
                Task creation options.

            Returns
            -------
            None
                No return value.
            """
            rejected.append(coroutine)
            raise failure

        loop.set_task_factory(reject)
        try:
            with self.assertRaises(RuntimeError) as caught:
                await transport._accept(self.frame(), self.writer)
        finally:
            loop.set_task_factory(factory)
        try:
            self.assertIs(caught.exception, failure)
            self.assertEqual(transport._active, {})
            self.assertEqual(
                [inspect.getcoroutinestate(item) for item in rejected],
                [inspect.CORO_CLOSED],
            )
        finally:
            for coroutine in rejected:
                coroutine.close()

    async def testCancellationSuppressesResultAndReaderRemainsLive(self):
        """Process cancellation on the shared channel while the tool is suspended.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.app.gates[1] = asyncio.Event()
        transport = self.transport()
        running = asyncio.create_task(transport.run(self.reader, self.writer))
        await self.reader.queue.put(self.frame(1))
        await self.app.started.get()
        await self.reader.queue.put(
            msgspec.json.encode(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/cancelled",
                    "params": {"requestId": 1},
                },
            )
            + b"\n",
        )
        self.assertEqual(await asyncio.wait_for(self.app.cancelled.get(), 1), 1)
        await self.reader.queue.put(self.frame(2))
        self.assertEqual((await asyncio.wait_for(self.writer.queue.get(), 1))["id"], 2)
        await self.finish(running)
        self.assertEqual(len(self.writer.writes), 1)

    async def testEofCancelsWorkAndJoinsScopeCleanup(self):
        """Closing stdin disposes work without emitting late protocol output.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.app.gates[1] = asyncio.Event()
        transport = self.transport()
        running = asyncio.create_task(transport.run(self.reader, self.writer))
        await self.reader.queue.put(self.frame())
        await self.app.started.get()
        await self.finish(running)
        self.assertEqual(await self.app.cancelled.get(), 1)
        self.assertFalse(self.app.scopes[1].isActive)
        self.assertEqual(self.writer.writes, [])

    async def testCapacityAndDuplicateIdsDoNotAllocateMoreWork(self):
        """Keep admission bounded and retain the original task on an ID collision.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.app.gates[1] = asyncio.Event()
        transport = self.transport(max_concurrent_requests=1)
        running = asyncio.create_task(transport.run(self.reader, self.writer))
        await self.reader.queue.put(self.frame())
        await self.app.started.get()
        await self.reader.queue.put(self.frame())
        duplicate = await asyncio.wait_for(self.writer.queue.get(), 1)
        self.assertEqual(duplicate["error"]["code"], -32600)
        await self.reader.queue.put(self.frame(2))
        capacity = await asyncio.wait_for(self.writer.queue.get(), 1)
        self.assertEqual(capacity["error"]["code"], -32603)
        self.assertEqual(len(transport._active), 1)
        await self.finish(running)

    async def testMalformedFramesDoNotTerminateHealthyTransport(self):
        """Reject malformed JSON and response messages, then accept a valid request.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        transport = self.transport()
        running = asyncio.create_task(transport.run(self.reader, self.writer))
        for frame, code in (
            (b"{\n", -32700),
            (b"[]\n", -32600),
            (b'{"jsonrpc":"2.0","id":1,"result":{}}\n', -32600),
        ):
            await self.reader.queue.put(frame)
            result = await asyncio.wait_for(self.writer.queue.get(), 1)
            self.assertEqual(result["error"]["code"], code)
            self.assertNotIn("id", result)
        await self.reader.queue.put(self.frame())
        self.assertEqual((await asyncio.wait_for(self.writer.queue.get(), 1))["id"], 1)
        await self.finish(running)

    async def testBrokenWriterTerminatesReaderAndCleansTasks(self):
        """A failed output pipe must not leave the owner stuck waiting for stdin.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        transport = self.transport()
        self.writer.broken = True
        running = asyncio.create_task(transport.run(self.reader, self.writer))
        await self.reader.queue.put(self.frame())
        with self.assertRaises(BrokenPipeError):
            await asyncio.wait_for(running, 1)
        self.assertEqual(transport._active, {})
        self.assertFalse(self.app.scopes[1].isActive)

    async def testDaemonStandardIoBoundsOversizedFrameAndResumes(self):
        """Read giant lines in bounded chunks and write without executor workers.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        reader = StandardReader(io.BytesIO(b"x" * 100 + b"\nnext\n"), 16)
        output = io.BytesIO()
        writer = StandardWriter(output)
        try:
            oversized = await asyncio.wait_for(reader.readline(), 1)
            self.assertLessEqual(len(oversized), 18)
            self.assertEqual(await asyncio.wait_for(reader.readline(), 1), b"next\n")
            self.assertEqual(await asyncio.wait_for(reader.readline(), 1), b"")
            await asyncio.wait_for(writer.write(b'{"ok":true}\n'), 1)
            self.assertEqual(output.getvalue(), b'{"ok":true}\n')
        finally:
            reader.close()
            writer.close()

    async def testDaemonWritesTheCompleteFrameAcrossShortWrites(self) -> None:
        """Acknowledge a frame only after every byte and its flush succeed.

        Returns
        -------
        None
            No return value.
        """
        output = _ShortOutput(3)
        writer = StandardWriter(output)
        data = b'{"value":"complete"}\n'
        try:
            await asyncio.wait_for(writer.write(data), 1)
            self.assertEqual(output.getvalue(), data)
            self.assertEqual(output.flushes, 1)
        finally:
            writer.close()

    async def testDaemonRejectsZeroProgressWithoutAcknowledgingSuccess(self) -> None:
        """Surface blocked writes instead of discarding the remainder of a frame.

        Returns
        -------
        None
            No return value.
        """
        for limit in (None, 0):
            with self.subTest(limit=limit):
                output = _ShortOutput(limit)
                writer = StandardWriter(output)
                try:
                    with self.assertRaises(OSError):
                        await asyncio.wait_for(writer.write(b"frame\n"), 1)
                    self.assertEqual(output.flushes, 0)
                finally:
                    writer.close()
