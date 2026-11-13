"""
Provide http adapters response operations.

Includes ``close_stream``, ``await_cleanup``, ``send_until_disconnect``.
"""

from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING
from orionis.failure.runtime import capture

if TYPE_CHECKING:
    from asyncio import Future, Task
    from collections.abc import AsyncIterable, Coroutine, Iterable, Iterator

_CLEANUP_PHASE = "stream.cleanup"
"""Central reporting phase shared by response-stream finalizers."""


class _SyncStreamIterator(AsyncIterator[bytes]):
    """Own a synchronous byte source before its first asynchronous read."""

    __slots__ = ("_iterator", "_source")
    """Retain the source and its lazily initialized iterator."""

    def __init__(self, source: Iterable[bytes]) -> None:
        """Retain the source without starting iteration.

        Parameters
        ----------
        source : collections.abc.Iterable[bytes]
            Synchronous response body whose closure is transferred to this wrapper.

        Returns
        -------
        None
            No return value.
        """
        self._source: Iterable[bytes] | None = source
        """Owned source, cleared when cleanup begins."""
        self._iterator: Iterator[bytes] | None = None
        """Iterator created only when the first body chunk is requested."""

    async def __anext__(self) -> bytes:
        """Read one byte chunk and close the source on exhaustion.

        Returns
        -------
        bytes
            Next chunk, copying mutable byte buffers.

        Raises
        ------
        StopAsyncIteration
            If the source is closed or exhausted.
        TypeError
            If the source yields a non-byte value.
        """
        if self._source is None:
            raise StopAsyncIteration
        if self._iterator is None:
            self._iterator = iter(self._source)
        try:
            chunk = next(self._iterator)
        except StopIteration:
            await self.aclose()
            raise StopAsyncIteration from None
        if isinstance(chunk, bytes):
            return chunk
        if isinstance(chunk, (bytearray, memoryview)):
            return bytes(chunk)
        error_msg = "StreamingResponse chunks must be bytes"
        raise TypeError(error_msg)

    async def aclose(self) -> None:
        """Close the active iterator or the unstarted source exactly once.

        Returns
        -------
        None
            No return value.
        """
        source, self._source = self._source, None
        if source is None:
            return
        target = source if self._iterator is None else self._iterator
        self._iterator = None
        close_async = getattr(target, "aclose", None)
        if close_async is not None:
            await close_async()
        else:
            close_sync = getattr(target, "close", None)
            if close_sync is not None:
                close_sync()


async def close_stream(
    iterator: AsyncIterable[bytes] | None,
    failure: BaseException | None,
) -> None:
    """
    Close an iterator without letting cleanup erase a delivery failure.

    Parameters
    ----------
    iterator : collections.abc.AsyncIterable[bytes] | None
        Owned source whose optional asynchronous close must be awaited, if present.
    failure : BaseException | None
        Producer or transport failure already propagating through cleanup.

    Returns
    -------
    None
        Finish cleanup, retaining a real delivery error if cancellation races it.
    """
    close = getattr(iterator, "aclose", None)
    if close is not None:
        try:
            await close()
            return
        except BaseException as close_error:
            if isinstance(failure, Exception):
                await capture(failure, flow="http", phase="stream")
            if isinstance(close_error, Exception):
                await capture(close_error, flow="http", phase=_CLEANUP_PHASE)
            preserve_failure = isinstance(failure, (Exception, BaseExceptionGroup))
            preserve_failure = preserve_failure or isinstance(
                close_error,
                asyncio.CancelledError,
            )
            if failure is None or not preserve_failure:
                raise
        raise failure


async def _finish_cancelled_cleanup[T](
    pending: Future[T],
    ready: Future[Future[T]],
) -> None:
    """
    Join owned cleanup after cancellation and retain its failure cause.

    Parameters
    ----------
    pending : asyncio.Future[``T``]
        Cleanup operation which must finish before its owner returns.
    ready : asyncio.Future[asyncio.Future[``T``]]
        Completion notification carrying no cleanup exception.

    Returns
    -------
    None
        Finish cleanup while deferring additional cancellation requests.

    """
    while not pending.done():
        with suppress(asyncio.CancelledError):
            await asyncio.shield(ready)
    if not pending.cancelled():
        failure = pending.exception()
        if failure is not None:
            await capture(failure, flow="http", phase=_CLEANUP_PHASE)


async def await_cleanup[T](pending: Future[T]) -> T:
    """
    Await owned cleanup before propagating cancellation to its caller.

    Parameters
    ----------
    pending : asyncio.Future[``T``]
        Cleanup operation protected from cancellation of its owner.

    Returns
    -------
    ``T``
        Completed cleanup result when the owner was not cancelled.

    Raises
    ------
    BaseException
        Propagate cleanup failure, or cancellation after successful cleanup.
    """
    if pending.done():
        return pending.result()
    ready = asyncio.get_running_loop().create_future()
    record = partial(_record_completion, ready)
    pending.add_done_callback(record)
    cancellation_cause = None
    try:
        try:
            await asyncio.shield(ready)
        except asyncio.CancelledError as cancellation:
            await _finish_cancelled_cleanup(pending, ready)
            if pending.cancelled() or pending.exception() is None:
                raise
            failure = pending.exception()
            has_chain = failure.__cause__ is not None or failure.__context__ is not None
            if not has_chain and not failure.__suppress_context__:
                cancellation_cause = cancellation
        if cancellation_cause is not None:
            raise pending.exception() from cancellation_cause
        return pending.result()
    finally:
        pending.remove_done_callback(record)


def _raise_task_errors(results: list[BaseException | None]) -> None:
    """
    Propagate real sender and watcher failures after both tasks finish.

    Parameters
    ----------
    results : list[BaseException | None]
        Outcomes collected from both owned response tasks.

    Returns
    -------
    None
        Return when both tasks succeeded or were cancelled.

    Raises
    ------
    BaseException
        Preserve one failure or group simultaneous failures.
    """
    errors = [
        result
        for result in results
        if isinstance(result, BaseException)
        and not isinstance(result, asyncio.CancelledError)
    ]
    if len(errors) == 1:
        raise errors[0]
    if errors:
        error_msg = "Event stream delivery and disconnect watcher failed"
        raise BaseExceptionGroup(error_msg, errors)


async def _cancel_tasks(tasks: tuple[Task[None], Task[None]]) -> None:
    """
    Cancel and join both owned tasks without abandoning asynchronous cleanup.

    Parameters
    ----------
    tasks : tuple[asyncio.Task[None], asyncio.Task[None]]
        Sender and disconnect watcher owned by one response.

    Returns
    -------
    None
        Finish both tasks before propagating their errors or cancellation.
    """
    for task in tasks:
        if not task.done():
            task.cancel()
    pending = asyncio.gather(*tasks, return_exceptions=True)
    try:
        results = await await_cleanup(pending)
    except asyncio.CancelledError:
        _raise_task_errors(pending.result())
        raise
    _raise_task_errors(results)


def _record_completion[T](
    first: Future[Future[T]],
    completed: Future[T],
) -> None:
    """
    Record the first completed future in event-loop callback order.

    Parameters
    ----------
    first : asyncio.Future[asyncio.Future[``T``]]
        Completion notification awaited by the stream coordinator or cleanup.
    completed : asyncio.Future[``T``]
        Operation whose completion triggered this callback.

    Returns
    -------
    None
        Preserve the first completion without changing a cancelled result.
    """
    if not first.done():
        first.set_result(completed)


async def send_until_disconnect(
    sending: Coroutine[None, None, None],
    disconnected: Coroutine[None, None, None],
) -> bool:
    """
    Race a stream delivery against the transport's disconnect notification.

    Parameters
    ----------
    sending : collections.abc.Coroutine[None, None, None]
        Delivery operation, including iterator cleanup and final framing.
    disconnected : collections.abc.Coroutine[None, None, None]
        Operation returning when the client disconnects.

    Returns
    -------
    bool
        Whether delivery completed before the disconnect watcher.

    Raises
    ------
    BaseException
        Propagate delivery, notification, cleanup errors or request cancellation.
    """
    sender = None
    try:
        sender = asyncio.create_task(sending, name="orionis.sse.send")
        watcher = asyncio.create_task(disconnected, name="orionis.sse.disconnect")
    except BaseException:
        disconnected.close()
        if sender is None:
            sending.close()
        else:
            sender.cancel()
            outcomes = await await_cleanup(
                asyncio.gather(sender, return_exceptions=True),
            )
            for error in outcomes:
                if isinstance(error, Exception):
                    await capture(error, flow="http", phase=_CLEANUP_PHASE)
        raise
    tasks = (sender, watcher)
    first = asyncio.get_running_loop().create_future()
    record = partial(_record_completion, first)
    sender.add_done_callback(record)
    watcher.add_done_callback(record)
    try:
        completed = await first
        if watcher.done():
            watcher.result()
        if sender.done():
            sender.result()
        return completed is sender
    finally:
        sender.remove_done_callback(record)
        watcher.remove_done_callback(record)
        await _cancel_tasks(tasks)
