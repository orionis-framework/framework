from __future__ import annotations
import asyncio
from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Future, Task
    from collections.abc import AsyncIterable, Coroutine

async def close_stream(
    iterator: AsyncIterable[bytes] | None, failure: BaseException | None,
) -> None:
    """
    Close an iterator without letting sibling cancellation erase a failure.

    Parameters
    ----------
    iterator : AsyncIterable[bytes] | None
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
        except BaseException as close_error:
            if failure is not None and isinstance(close_error, asyncio.CancelledError):
                raise failure from close_error
            raise

async def _finish_cancelled_cleanup[T](
    pending: Future[T],
    ready: Future[Future[T]],
    cancellation: asyncio.CancelledError,
) -> None:
    """
    Join owned cleanup after cancellation and retain its failure cause.

    Parameters
    ----------
    pending : Future[T]
        Cleanup operation which must finish before its owner returns.
    ready : Future[Future[T]]
        Completion notification carrying no cleanup exception.
    cancellation : asyncio.CancelledError
        Cancellation that the owner will re-raise after cleanup succeeds.

    Returns
    -------
    None
        Finish cleanup while deferring additional cancellation requests.

    Raises
    ------
    BaseException
        If cleanup fails, chain its error to the original cancellation.
    """
    while not pending.done():
        with suppress(asyncio.CancelledError):
            await asyncio.shield(ready)
    if not pending.cancelled():
        failure = pending.exception()
        if failure is not None:
            raise failure from cancellation

async def await_cleanup[T](pending: Future[T]) -> T:
    """
    Await owned cleanup before propagating cancellation to its caller.

    Parameters
    ----------
    pending : Future[T]
        Cleanup operation protected from cancellation of its owner.

    Returns
    -------
    T
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
    try:
        try:
            await asyncio.shield(ready)
        except asyncio.CancelledError as cancellation:
            await _finish_cancelled_cleanup(pending, ready, cancellation)
            raise
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
        result for result in results
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
    tasks : tuple[Task[None], Task[None]]
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
    first: Future[Future[T]], completed: Future[T],
) -> None:
    """
    Record the first completed future in event-loop callback order.

    Parameters
    ----------
    first : Future[Future[T]]
        Completion notification awaited by the stream coordinator or cleanup.
    completed : Future[T]
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
    sending : Coroutine[None, None, None]
        Delivery operation, including iterator cleanup and final framing.
    disconnected : Coroutine[None, None, None]
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
    sender = asyncio.create_task(sending, name="orionis.sse.send")
    watcher = asyncio.create_task(disconnected, name="orionis.sse.disconnect")
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
