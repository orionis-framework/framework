"""Bounded daemon I/O bridges that never occupy the event loop's executor."""

from __future__ import annotations

import asyncio
from concurrent.futures import CancelledError
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from concurrent.futures import Future
    from typing import BinaryIO


class StandardReader:
    """Read at most one queued frame using an interruptible async queue boundary."""

    __slots__ = ("_closed", "_limit", "_loop", "_pending", "_queue", "_stream")

    def __init__(self, stream: BinaryIO, limit: int) -> None:
        """Start one daemon so an idle Windows pipe cannot delay executor shutdown."""
        self._stream = stream
        self._limit = limit
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[bytes | OSError] = asyncio.Queue(maxsize=1)
        self._closed = threading.Event()
        self._pending: Future[None] | None = None
        threading.Thread(
            target=self._read, name="orionis.mcp.stdin", daemon=True,
        ).start()

    def _offer(self, item: bytes | OSError) -> bool:
        """Apply queue backpressure in the daemon rather than allocating callbacks."""
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
        """Read bounded chunks and drain oversized frames without accumulating them."""
        try:
            while not self._closed.is_set():
                line = self._stream.readline(self._limit + 2)
                if not self._offer(line) or not line:
                    return
                while len(line) > self._limit and not line.endswith(b"\n"):
                    if self._closed.is_set():
                        return
                    line = self._stream.readline(self._limit + 2)
                    if not line:
                        self._offer(b"")
                        return
        except OSError as exc:
            self._offer(exc)

    async def readline(self) -> bytes:
        """Return the next frame or propagate a real input transport failure."""
        value = await self._queue.get()
        if isinstance(value, OSError):
            raise value
        return value

    def close(self) -> None:
        """Stop future deliveries without waiting on an uninterruptible OS read."""
        self._closed.set()
        if self._pending is not None:
            self._pending.cancel()


def _finish_write(future: asyncio.Future[None], error: OSError | None) -> None:
    """Resolve delivery only on the owning loop, ignoring canceled callers."""
    if not future.done():
        if error is None:
            future.set_result(None)
        else:
            future.set_exception(error)


class StandardWriter:
    """Serialize bounded queued output without blocking async cancellation."""

    __slots__ = ("_closed", "_loop", "_pending", "_queue", "_stream")

    def __init__(self, stream: BinaryIO) -> None:
        """Start one daemon dedicated to the captured binary protocol channel."""
        self._stream = stream
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[tuple[bytes, asyncio.Future[None]]] = asyncio.Queue(
            1,
        )
        self._closed = threading.Event()
        self._pending: Future[tuple[bytes, asyncio.Future[None]]] | None = None
        threading.Thread(
            target=self._write, name="orionis.mcp.stdout", daemon=True,
        ).start()

    def _write(self) -> None:
        """Write whole frames and acknowledge flush completion with backpressure."""
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
                self._stream.write(data)
                self._stream.flush()
            except OSError as exc:
                error = exc
            try:
                self._loop.call_soon_threadsafe(_finish_write, completed, error)
            except RuntimeError:
                return

    async def write(self, data: bytes) -> None:
        """Wait for one complete protocol frame to reach the output stream."""
        completed: asyncio.Future[None] = self._loop.create_future()
        await self._queue.put((data, completed))
        await completed

    def close(self) -> None:
        """Stop queued output without joining a potentially blocked OS writer."""
        self._closed.set()
        if self._pending is not None:
            self._pending.cancel()
