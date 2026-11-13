# ruff: noqa: BLE001
# Reader/writer boundaries deliver or report all ordinary failures to their owners.
"""Provide mcp transport operations through ``StandardReader``, ``StandardWriter``."""

from __future__ import annotations
import asyncio
from concurrent.futures import CancelledError, Future
import threading
from typing import BinaryIO
from orionis.failure.runtime import FailureRuntime, capture_nowait, get_runtime


class StandardReader:
    """Read at most one queued frame using an interruptible async queue boundary."""

    __slots__ = (
        "_closed",
        "_failure",
        "_failure_lock",
        "_limit",
        "_loop",
        "_pending",
        "_queue",
        "_runtime",
        "_stream",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        stream: BinaryIO,
        limit: int,
        *,
        runtime: FailureRuntime | None = None,
    ) -> None:
        """
        Start a daemon reader with bounded delivery to the running event loop.

        Parameters
        ----------
        stream : typing.BinaryIO
            Binary input stream supporting bounded ``readline`` calls.
        limit : int
            Frame-size threshold; each read requests up to ``limit + 2`` bytes.
        runtime : orionis.failure.runtime.FailureRuntime or None, optional
            Runtime retained for unread failures; use the current runtime if
            ``None``.

        Returns
        -------
        None
            Capture the running loop and start the reader's daemon thread.

        Raises
        ------
        RuntimeError
            If no event loop is running in the calling thread.
        """
        self._stream = stream
        """Value supplied for ``stream``."""
        self._limit = limit
        """Value supplied for ``limit``."""
        self._loop = asyncio.get_running_loop()
        """Loop produced by ``asyncio.get_running_loop``."""
        self._runtime = runtime if runtime is not None else get_runtime()
        """Runtime retained for failures after reader cancellation."""
        self._failure: Exception | None = None
        """Read failure awaiting either delivery or shutdown observation."""
        self._failure_lock = threading.Lock()
        """Transfer error ownership once between the daemon and event loop."""
        self._queue: asyncio.Queue[bytes | Exception] = asyncio.Queue(maxsize=1)
        """Name of the queue receiving or storing the job."""
        self._closed = threading.Event()
        """Whether this resource has completed its close lifecycle."""
        self._pending: Future[None] | None = None
        """Work that has been admitted and is awaiting completion."""
        threading.Thread(
            target=self._read,
            name="orionis.mcp.stdin",
            daemon=True,
        ).start()

    def _offer(self, item: bytes | Exception) -> bool:
        """
        Offer one input item with backpressure on the reader's daemon thread.

        Parameters
        ----------
        item : bytes | Exception
            Input chunk, EOF marker ``b""``, or read exception to deliver.

        Returns
        -------
        bool
            ``True`` if the put completes and the reader is still open;
            ``False`` if delivery stops, is cancelled, or cannot be scheduled.
        """
        if self._closed.is_set():
            return False
        operation = self._queue.put(item)
        try:
            self._pending = asyncio.run_coroutine_threadsafe(operation, self._loop)
        except RuntimeError:
            operation.close()
            return False
        try:
            self._pending.result()
        except CancelledError:
            return False
        return not self._closed.is_set()

    def _read(self) -> None:
        """
        Read bounded input chunks and discard oversized frame remainders.

        Forward read errors to the asynchronous consumer, or observe them if
        shutdown prevents delivery.

        Returns
        -------
        None
            Finish on end of input, shutdown, or a read failure.
        """
        try:
            while not self._closed.is_set():
                line = self._stream.readline(self._limit + 2)
                if not self._offer(line) or not line:
                    return
                if (
                    len(line) > self._limit
                    and not line.endswith(b"\n")
                    and not self._drainOversizedFrame()
                ):
                    return
        except Exception as exc:
            with self._failure_lock:
                self._failure = exc
            if not self._offer(exc):
                self._reportFailure()

    def _drainOversizedFrame(self) -> bool:
        """
        Discard the unread remainder of an oversized input frame.

        Returns
        -------
        bool
            ``True`` when draining completes; ``False`` on shutdown or an empty
            read. Forward an empty read as the end-of-input marker.
        """
        while not self._closed.is_set():
            line = self._stream.readline(self._limit + 2)
            if not line:
                self._offer(b"")
                return False
            if len(line) <= self._limit or line.endswith(b"\n"):
                return True
        return False

    def _takeFailure(self) -> Exception | None:
        """
        Claim and clear the pending read failure atomically.

        Returns
        -------
        Exception or None
            Unread exception removed from shared state, or ``None`` when none
            is pending.
        """
        with self._failure_lock:
            failure, self._failure = self._failure, None
            return failure

    def _reportFailure(self) -> None:
        """
        Claim and observe any unread input failure once.

        Returns
        -------
        None
            Submit a claimed failure with stdio metadata, or do nothing when
            no failure remains.
        """
        failure = self._takeFailure()
        if failure is not None:
            capture_nowait(
                failure,
                runtime=self._runtime,
                flow="mcp",
                phase="read",
                metadata={"transport": "stdio"},
            )

    async def readline(self) -> bytes:
        """
        Await the next bounded input chunk or propagate a queued read failure.

        Returns
        -------
        bytes
            Next queued bytes, including any newline, or ``b""`` for end of input.

        Raises
        ------
        Exception
            If the reader queued an input-stream failure.
        asyncio.CancelledError
            If the coroutine is cancelled while waiting for input.
        """
        value = await self._queue.get()
        if isinstance(value, Exception):
            self._takeFailure()
            raise value
        return value

    def close(self) -> None:
        """
        Stop input delivery without waiting for a blocked operating-system read.

        Do not close the input stream or join the daemon thread.

        Returns
        -------
        None
            Mark the reader closed, observe unread failures, and cancel a pending
            queue put.
        """
        self._closed.set()
        self._reportFailure()
        if self._pending is not None:
            self._pending.cancel()


def _finish_write(
    future: asyncio.Future[None],
    error: Exception | None,
    runtime: FailureRuntime | None = None,
) -> None:
    """
    Settle a write future on its owning loop or observe a late write error.

    Parameters
    ----------
    future : asyncio.Future[None]
        Delivery acknowledgement to settle; leave completed futures unchanged.
    error : Exception or None
        Write or flush error, or ``None`` for successful delivery.
    runtime : orionis.failure.runtime.FailureRuntime or None, optional
        Runtime used to observe errors after the acknowledgement has finished.

    Returns
    -------
    None
        Settle a pending acknowledgement, or observe an error if it is already done.
    """
    if not future.done():
        if error is None:
            future.set_result(None)
        else:
            future.set_exception(error)
    elif error is not None:
        capture_nowait(
            error,
            runtime=runtime,
            flow="mcp",
            phase="write",
            metadata={"transport": "stdio"},
        )


class StandardWriter:
    """Serialize bounded queued output without blocking async cancellation."""

    __slots__ = ("_closed", "_loop", "_pending", "_queue", "_runtime", "_stream")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        stream: BinaryIO,
        *,
        runtime: FailureRuntime | None = None,
    ) -> None:
        """
        Start a daemon writer with a single-slot queue on the running loop.

        Parameters
        ----------
        stream : typing.BinaryIO
            Binary output stream receiving unchanged queued bytes.
        runtime : orionis.failure.runtime.FailureRuntime or None, optional
            Runtime retained for late write failures; use the current runtime if
            ``None``.

        Returns
        -------
        None
            Capture the running loop and start the writer's daemon thread.

        Raises
        ------
        RuntimeError
            If no event loop is running in the calling thread.
        """
        self._stream = stream
        """Value supplied for ``stream``."""
        self._loop = asyncio.get_running_loop()
        """Loop produced by ``asyncio.get_running_loop``."""
        self._runtime = runtime if runtime is not None else get_runtime()
        """Runtime retained for errors after output waiters are cancelled."""
        self._queue: asyncio.Queue[tuple[bytes, asyncio.Future[None]]] = asyncio.Queue(
            1,
        )
        """Name of the queue receiving or storing the job."""
        self._closed = threading.Event()
        """Whether this resource has completed its close lifecycle."""
        self._pending: Future[tuple[bytes, asyncio.Future[None]]] | None = None
        """Work that has been admitted and is awaiting completion."""
        threading.Thread(
            target=self._write,
            name="orionis.mcp.stdout",
            daemon=True,
        ).start()

    def _write(self) -> None:
        """
        Write queued bytes and settle acknowledgements after flushing.

        Skip acknowledgements cancelled before writing. Deliver stream errors
        through the owning loop, observing failures whose caller no longer waits.

        Returns
        -------
        None
            Exit on shutdown, queue-wait cancellation, or event-loop closure.
        """
        while not self._closed.is_set():
            operation = self._queue.get()
            try:
                self._pending = asyncio.run_coroutine_threadsafe(operation, self._loop)
            except RuntimeError:
                operation.close()
                return
            try:
                data, completed = self._pending.result()
            except CancelledError:
                return
            if completed.cancelled() or self._closed.is_set():
                continue
            error = None
            try:
                self._writeFrame(data)
            except Exception as exc:
                error = exc
            try:
                self._loop.call_soon_threadsafe(
                    _finish_write,
                    completed,
                    error,
                    self._runtime,
                )
            except RuntimeError:
                if error is not None:
                    capture_nowait(
                        error,
                        runtime=self._runtime,
                        flow="mcp",
                        phase="write",
                        metadata={"transport": "stdio"},
                    )
                return

    def _writeFrame(self, data: bytes) -> None:
        """Complete partial raw-stream writes before flushing one frame.

        Parameters
        ----------
        data : bytes
            Entire frame owned by the writer daemon.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        OSError
            If the stream makes no progress or returns an invalid byte count.
        """
        remaining = memoryview(data)
        while remaining:
            written = self._stream.write(remaining)
            if type(written) is not int or not 0 < written <= len(remaining):
                message = "STDIO output did not accept the remaining frame bytes"
                raise OSError(message)
            remaining = remaining[written:]
        self._stream.flush()

    async def write(self, data: bytes) -> None:
        """
        Queue unchanged bytes and wait for the output stream to flush them.

        Cancellation does not interrupt an operating-system write already
        in progress.

        Parameters
        ----------
        data : bytes
            Protocol bytes to write, including any required frame delimiter.

        Returns
        -------
        None
            Complete after the daemon's write and flush calls succeed.

        Raises
        ------
        Exception
            If the output stream's write or flush operation fails.
        asyncio.CancelledError
            If the caller is cancelled while enqueueing or awaiting delivery.
        """
        completed: asyncio.Future[None] = self._loop.create_future()
        await self._queue.put((data, completed))
        await completed

    def close(self) -> None:
        """
        Stop queued output without waiting for a blocked operating-system write.

        Do not close the output stream or join the daemon thread.

        Returns
        -------
        None
            Mark the writer closed and cancel a pending queue get without draining
            queued output.
        """
        self._closed.set()
        if self._pending is not None:
            self._pending.cancel()
