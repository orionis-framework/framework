# ruff: noqa: TC001, TC003
# Runtime service construction and transport reflection consume these annotations.
"""Provide mcp transport operations.

Includes ``LineReader``, ``LineWriter``, ``McpStdioTransport``.
"""

from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator
from contextlib import redirect_stdout
from functools import partial
import sys
from typing import Protocol
import msgspec
from orionis.failure.runtime import capture, capture_nowait, get_runtime, operation
from orionis.http.adapters.response.streams import await_cleanup
from orionis.console.stdio import protocol_stdout
from orionis.mcp.dispatcher import McpDispatcher
from orionis.mcp.exceptions import McpProtocolException
from orionis.mcp.protocol.codecs import decode_envelope, encode_error
from orionis.mcp.protocol.requests import CancelledParams
from orionis.mcp.reporting import report
from orionis.mcp.streams import _create_task
from orionis.mcp.transport.standard_io import StandardReader, StandardWriter
from orionis.foundation.contracts.application import IApplication
from orionis.mcp.config import McpConfig
from orionis.mcp.contracts.event_bus import IMcpEventBus
from orionis.mcp.protocol.requests import JsonRpcRequest
from orionis.mcp.server.compiler import CompiledMcpServer


class LineReader(Protocol):
    """Provide one bounded input frame or empty bytes at EOF."""

    async def readline(self) -> bytes:
        """
        Read one newline-delimited wire message.

        Returns
        -------
        bytes
            Result of the operation described above.
        """
        ...


class LineWriter(Protocol):
    """Write a complete message with backpressure."""

    async def write(self, data: bytes) -> None:
        """
        Deliver a complete frame, including its terminating newline.

        Parameters
        ----------
        data : bytes
            Value supplied for ``data``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        ...


class McpStdioTransport:
    """Keep the reader available while bounded request tasks execute independently."""

    __slots__ = (
        "_active",
        "_app",
        "_closing",
        "_config",
        "_dispatcher",
        "_failed",
        "_failure",
        "_lock",
        "_reports",
        "_running",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        app: IApplication,
        compiled: CompiledMcpServer,
        config: McpConfig,
        bus: IMcpEventBus,
    ) -> None:
        """
        Prepare request-local task ownership without touching process streams.

        Parameters
        ----------
        app : orionis.IApplication
            Application container supplying configuration and dependencies.
        compiled : orionis.mcp.server.compiler.CompiledMcpServer
            Precompiled metadata shared by request executions.
        config : orionis.mcp.config.McpConfig
            Validated configuration controlling this component.
        bus : orionis.mcp.contracts.event_bus.IMcpEventBus
            Value supplied for ``bus``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._app = app
        """Application container supplying configuration and dependencies."""
        self._config = config
        """Validated configuration controlling this component."""
        self._dispatcher = McpDispatcher(app, compiled, config, bus)
        """Dispatcher produced by ``McpDispatcher``."""
        self._active: dict[str | int, asyncio.Task[None]] = {}
        """Operations currently running for this connection or transport."""
        self._lock = asyncio.Lock()
        """Lock protecting concurrent access to shared state."""
        self._failed = asyncio.Event()
        """Backend retaining failed-job records."""
        self._failure: BaseException | None = None
        """Failure retained for propagation or reporting."""
        self._reports: set[asyncio.Future] = set()
        """Failure delivery tasks owned until transport shutdown."""
        self._closing = False
        """Whether resource cleanup is currently in progress."""
        self._running = False
        """Running flag used by ``McpStdioTransport``."""

    async def _write(self, writer: LineWriter, data: bytes) -> None:
        """
        Serialize frames and suppress output after EOF or owner shutdown.

        Parameters
        ----------
        writer : orionis.mcp.transport.stdio.LineWriter
            Output stream receiving complete messages with backpressure.
        data : bytes
            Value supplied for ``data``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if not data or self._closing:
            return
        async with self._lock:
            if not self._closing:
                await writer.write(data + b"\n")

    async def _stream(self, writer: LineWriter, source: AsyncIterator[bytes]) -> None:
        """
        Preserve backpressure and close an owned producer on all exits.

        Parameters
        ----------
        writer : orionis.mcp.transport.stdio.LineWriter
            Output stream receiving complete messages with backpressure.
        source : collections.abc.AsyncIterator[bytes]
            Source whose values or lifecycle are consumed by this operation.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        original = None
        try:
            async for data in source:
                await self._write(writer, data)
        except BaseException as exc:
            original = exc
            await capture(
                exc,
                app=self._app,
                flow="mcp",
                phase="stream",
                metadata={"transport": "stdio"},
            )
            raise
        finally:
            close = getattr(source, "aclose", None)
            if close is not None:
                try:
                    await await_cleanup(asyncio.ensure_future(close()))
                except BaseException as exc:
                    await capture(
                        exc,
                        app=self._app,
                        flow="mcp",
                        phase="cleanup",
                        metadata={"transport": "stdio"},
                    )
                    if original is None:
                        raise

    async def _invoke(self, request: JsonRpcRequest, writer: LineWriter) -> None:
        """
        Execute one call in its own DI scope, sanitizing only application errors.

        Parameters
        ----------
        request : orionis.mcp.protocol.requests.JsonRpcRequest
            Current request and its trusted execution context.
        writer : orionis.mcp.transport.stdio.LineWriter
            Output stream receiving complete messages with backpressure.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        with operation(
            self._app,
            flow="mcp",
            operation=request.method,
            correlation_id=str(request.id),
            isolated=True,
        ):
            try:
                async with self._app.beginScope():
                    params = self._dispatcher.decode(request)
                    result = await self._dispatcher.dispatch(
                        request,
                        params,
                        transport="stdio",
                    )
                    if isinstance(result.body, bytes):
                        await self._write(writer, result.body)
                    else:
                        await self._stream(writer, result.body)
            except McpProtocolException as exc:
                await report(
                    exc,
                    self._app,
                    transport="stdio",
                    expected=True,
                    operation=request.method,
                    correlation_id=request.id,
                )
                await self._write(writer, encode_error(exc, request.id))
            except BaseException as exc:
                await report(
                    exc,
                    self._app,
                    transport="stdio",
                    phase="request",
                    operation=request.method,
                    correlation_id=request.id,
                )
                raise

    def _done(self, request_id: str | int, task: asyncio.Task[None]) -> None:
        """
        Remove completed task ownership and notify the reader of I/O failures.

        Parameters
        ----------
        request_id : str | int
            Value supplied for ``request_id``.
        task : asyncio.Task[None]
            Value supplied for ``task``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if self._active.get(request_id) is task:
            del self._active[request_id]
        if not task.cancelled() and (failure := task.exception()) is not None:
            pending = capture_nowait(
                failure,
                app=self._app,
                flow="mcp",
                phase="request",
                correlation_id=str(request_id),
                metadata={"transport": "stdio"},
            )
            if pending is not None:
                self._reports.add(pending)
                pending.add_done_callback(self._reports.discard)
            self._failure = failure
            self._failed.set()

    def _cancel(self, request: JsonRpcRequest) -> None:
        """
        Ignore malformed, unknown and already completed cancellation messages.

        Parameters
        ----------
        request : orionis.mcp.protocol.requests.JsonRpcRequest
            Current request and its trusted execution context.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if request.method != "notifications/cancelled":
            return
        try:
            params = msgspec.json.decode(request.params, type=CancelledParams)
        except (msgspec.DecodeError, msgspec.ValidationError) as exc:
            pending = capture_nowait(
                exc,
                app=self._app,
                flow="mcp",
                phase="cancellation",
                operation=request.method,
                expected=True,
                metadata={"transport": "stdio"},
            )
            if pending is not None:
                self._reports.add(pending)
                pending.add_done_callback(self._reports.discard)
            return
        task = self._active.get(params.requestId)
        if task is not None and not task.cancelling():
            task.cancel()

    async def _accept(self, data: bytes, writer: LineWriter) -> None:
        """
        Stop queued output without joining a potentially blocked OS writer.

        Parameters
        ----------
        data : bytes
            Value supplied for ``data``.
        writer : orionis.mcp.transport.stdio.LineWriter
            Output stream receiving complete messages with backpressure.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        request_id = msgspec.UNSET
        try:
            if len(data) > self._config.max_request_size:
                raise McpProtocolException(-32600, "Request frame too large")
            request = decode_envelope(data)
            request_id = request.id
            if request_id is msgspec.UNSET:
                self._cancel(request)
                return
            if request_id in self._active:
                raise McpProtocolException(-32600, "Duplicate active request ID")
            if len(self._active) >= self._config.max_concurrent_requests:
                raise McpProtocolException(
                    -32603,
                    "Request capacity unavailable",
                    status=503,
                )
            task = _create_task(
                self._invoke(request, writer),
                name="orionis.mcp.request",
            )
            self._active[request_id] = task
            task.add_done_callback(partial(self._done, request_id))
        except McpProtocolException as exc:
            await report(
                exc,
                self._app,
                transport="stdio",
                phase="framing",
                expected=True,
                correlation_id=None if request_id is msgspec.UNSET else request_id,
            )
            await self._write(writer, encode_error(exc, request_id))

    async def _readLoop(self, reader: LineReader, writer: LineWriter) -> None:
        """
        Race each cancellable read against a failed request's transport I/O.

        Parameters
        ----------
        reader : orionis.mcp.transport.stdio.LineReader
            Input stream supplying bounded messages.
        writer : orionis.mcp.transport.stdio.LineWriter
            Output stream receiving complete messages with backpressure.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        failed = _create_task(self._failed.wait())
        reading: asyncio.Task[bytes] | None = None
        try:
            while True:
                reading = _create_task(reader.readline())
                await asyncio.wait(
                    (reading, failed),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if self._failure is not None:
                    raise self._failure
                data = reading.result()
                if not data:
                    return
                await self._accept(data.removesuffix(b"\n").removesuffix(b"\r"), writer)
        finally:
            owned = (failed,) if reading is None else (failed, reading)
            for task in owned:
                if not task.done():
                    task.cancel()
            results = await await_cleanup(
                asyncio.gather(*owned, return_exceptions=True),
            )
            for failure in results:
                if isinstance(failure, BaseException):
                    await report(failure, self._app, transport="stdio", phase="read")

    async def run(self, reader: LineReader, writer: LineWriter) -> None:
        """
        Run until EOF, joining all owned request cleanup before returning.

        Parameters
        ----------
        reader : orionis.mcp.transport.stdio.LineReader
            Input stream supplying bounded messages.
        writer : orionis.mcp.transport.stdio.LineWriter
            Output stream receiving complete messages with backpressure.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if self._running:
            message = "The STDIO transport is already running"
            raise RuntimeError(message)
        self._running = True
        self._closing = False
        self._failure = None
        self._failed.clear()
        with operation(self._app, flow="mcp", operation="stdio"):
            try:
                await self._readLoop(reader, writer)
            except BaseException as exc:
                await report(exc, self._app, transport="stdio", phase="read")
                raise
            finally:
                self._closing = True
                tasks = tuple(self._active.values())
                for task in tasks:
                    if not task.cancelling():
                        task.cancel()
                try:
                    if tasks:
                        results = await await_cleanup(
                            asyncio.gather(*tasks, return_exceptions=True),
                        )
                        for failure in results:
                            if isinstance(failure, BaseException):
                                await report(
                                    failure,
                                    self._app,
                                    transport="stdio",
                                    phase="cleanup",
                                )
                    if self._failure is not None:
                        await capture(
                            self._failure,
                            app=self._app,
                            flow="mcp",
                            phase="cleanup",
                            metadata={"transport": "stdio"},
                        )
                    if self._reports:
                        await await_cleanup(asyncio.gather(*self._reports))
                finally:
                    self._active.clear()
                    self._reports.clear()
                    self._running = False

    async def runStandardStreams(self) -> None:
        """
        Bind portable daemon-backed streams and keep application prints on stderr.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        runtime = get_runtime(self._app)
        reader = StandardReader(
            sys.stdin.buffer,
            self._config.max_request_size,
            runtime=runtime,
        )
        writer = StandardWriter(
            protocol_stdout() or sys.stdout.buffer,
            runtime=runtime,
        )
        try:
            with redirect_stdout(sys.stderr):
                await self.run(reader, writer)
        finally:
            reader.close()
            writer.close()
