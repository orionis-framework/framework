from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from contextvars import copy_context
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

async def _wait_for_completion[T](
    future: asyncio.Future[T],
    *,
    on_cancel: Callable[[T], Awaitable[None]] | None = None,
) -> T:
    """
    Drain a worker result while shielding only a successful completion notice.

    Parameters
    ----------
    future : asyncio.Future[T]
        Worker operation whose result must be collected before cleanup.
    on_cancel : Callable[[T], Awaitable[None]] | None, optional
        Cleanup for resources completed after cancellation.

    Returns
    -------
    T
        Completed result when the caller was not cancelled.

    Raises
    ------
    BaseException
        Propagate worker failures unless cancellation already takes precedence.
    """
    notification = future.get_loop().create_future()

    def completed(_future: asyncio.Future[T]) -> None:
        """Publish a successful notice independently of the worker outcome.

        Parameters
        ----------
        _future : asyncio.Future[T]
            Completed operation; its result is collected by the caller.

        Returns
        -------
        None
            Wake the waiting task without forwarding a worker exception.
        """
        if not notification.done():
            notification.set_result(None)

    future.add_done_callback(completed)
    try:
        await asyncio.shield(notification)
    except asyncio.CancelledError:
        while not notification.done():
            with suppress(asyncio.CancelledError):
                await asyncio.shield(notification)
        if (
            not future.cancelled()
            and future.exception() is None
            and on_cancel is not None
        ):
            with suppress(asyncio.CancelledError):
                await on_cancel(future.result())
        raise
    return future.result()

class ThreadedWorker:
    """
    Serialize one checked-out DBAPI connection on one worker thread.

    Cancellation waits for blocking I/O to finish before releasing its connection.
    Operations on other checkouts use independent workers and remain concurrent.
    """

    __slots__ = ("_closed", "_executor")

    def __init__(self) -> None:
        """Prepare a worker without starting a thread or opening a connection.

        Returns
        -------
        None
            Initialize a lazy single-thread executor.
        """
        self._closed = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="orionis-redshift",
        )

    async def run[T](
        self,
        operation: Callable[[], T],
        *,
        on_cancel: Callable[[T], None] | None = None,
    ) -> T:
        """
        Execute blocking work and settle it before propagating cancellation.

        Parameters
        ----------
        operation : Callable[[], T]
            Blocking operation owned by this connection.
        on_cancel : Callable[[T], None] | None, optional
            Dispose a resource produced after its caller was cancelled.

        Returns
        -------
        T
            Completed operation result.

        Raises
        ------
        RuntimeError
            If the worker has already been closed.
        asyncio.CancelledError
            After blocking work and any required cancellation cleanup finish.
        """
        if self._closed:
            message = "The database worker is closed."
            raise RuntimeError(message)
        future = asyncio.get_running_loop().run_in_executor(
            self._executor, partial(copy_context().run, operation),
        )

        async def discard(value: T) -> None:
            """Release a late result on the same worker that created it.

            Parameters
            ----------
            value : T
                Resource produced after the caller was cancelled.

            Returns
            -------
            None
                Complete the supplied cancellation cleanup.
            """
            if on_cancel is not None:
                await self.run(partial(on_cancel, value))

        return await _wait_for_completion(
            future, on_cancel=discard if on_cancel is not None else None,
        )

    async def close(self) -> None:
        """Join this worker without blocking the event loop.

        Returns
        -------
        None
            Complete all submitted work and release the worker thread.

        Raises
        ------
        asyncio.CancelledError
            Only after executor shutdown has completed.
        """
        if self._closed:
            return
        self._closed = True
        future = asyncio.get_running_loop().run_in_executor(
            None, partial(self._executor.shutdown, wait=True),
        )
        await _wait_for_completion(future)
