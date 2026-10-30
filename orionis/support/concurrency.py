from __future__ import annotations
import asyncio
import contextvars
import inspect
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from threading import BoundedSemaphore, Lock
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

class WorkQueueFullError(RuntimeError):
    """Signal that a bounded worker pool cannot admit another operation."""

async def complete_on_cancel[T](
    awaitable: Awaitable[T],
    *,
    on_cancel: Callable[[], object] | None = None,
) -> T:
    """Wait for owned work before propagating caller cancellation.

    Parameters
    ----------
    awaitable : Awaitable[T]
        Operation that must finish before its resources can be released.
    on_cancel : Callable[[], object] | None
        Optional request to stop work that has not started yet.

    Returns
    -------
    T
        Operation result unless the caller was cancelled.
    """
    task = asyncio.ensure_future(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        if on_cancel is not None:
            on_cancel()
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError: # NOSONAR
                continue
            except Exception:  # noqa: BLE001
                break
        if not task.cancelled():
            task.exception()
        raise

class BoundedExecutor:
    """Own a lazy thread pool with bounded running and queued work.

    Admission is process-wide per instance, including across event loops.
    Cancellation waits for running native work; queued work is cancelled.
    """

    def __init__(
        self: Self,
        max_workers: int = 4,
        *,
        max_pending: int = 32,
        name: str = "orionis-worker",
    ) -> None:
        """
        Configure a lazy worker pool.

        Parameters
        ----------
        max_workers : int
            Maximum simultaneous native calls.
        max_pending : int
            Maximum additional queued calls; overload raises WorkQueueFullError.
        name : str
            Prefix used for worker thread names.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        if (
            isinstance(max_workers, bool)
            or not isinstance(max_workers, int)
            or max_workers < 1
            or isinstance(max_pending, bool)
            or not isinstance(max_pending, int)
            or max_pending < 0
        ):
            error_msg = (
                "Worker count must be positive and pending capacity nonnegative."
            )
            raise ValueError(error_msg)
        self._workers = max_workers
        self._name = name
        self._capacity = BoundedSemaphore(max_workers + max_pending)
        self._lock = Lock()
        self._pool: ThreadPoolExecutor | None = None
        self._closed = False

    async def run[T](
        self: Self,
        callback: Callable[..., T],
        /,
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute a synchronous callable with copied context and bounded admission.

        Parameters
        ----------
        callback : Callable[..., T]
            Synchronous operation with thread-safe dependencies.
        *args : object
            Positional callback arguments.
        **kwargs : object
            Keyword callback arguments.

        Returns
        -------
        T
            Result from the worker thread.
        """
        if not self._capacity.acquire(blocking=False):
            error_msg = f"Worker pool '{self._name}' is at capacity."
            raise WorkQueueFullError(error_msg)
        try:
            context = contextvars.copy_context()
            with self._lock:
                if self._closed:
                    error_msg = "Worker pool is closed."
                    raise RuntimeError(error_msg)
                if self._pool is None:
                    self._pool = ThreadPoolExecutor(
                        max_workers=self._workers,
                        thread_name_prefix=self._name,
                    )
                future = self._pool.submit(
                    context.run,
                    partial(callback, *args, **kwargs),
                )
        except BaseException:
            self._capacity.release()
            raise
        future.add_done_callback(lambda _future: self._capacity.release())
        return await complete_on_cancel(
            asyncio.wrap_future(future),
            on_cancel=future.cancel,
        )

    def close(self: Self) -> None:
        """Drain accepted work and release the pool's threads.

        Returns
        -------
        None
            Further submissions fail after close starts.
        """
        with self._lock:
            self._closed = True
            pool = self._pool
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)

    async def aclose(self: Self) -> None:
        """Close without blocking the event loop.

        Returns
        -------
        None
            Accepted running work is finished and threads are joined.
        """
        await complete_on_cancel(asyncio.to_thread(self.close))

_CALLBACK_WORKERS = BoundedExecutor(name="orionis-callback")

def threaded[**P, T](callback: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    """Opt a synchronous handler into bounded thread execution.

    Parameters
    ----------
    callback : Callable[P, T]
        Blocking synchronous function. Dependencies must support worker threads.

    Returns
    -------
    Callable[P, Awaitable[T]]
        Async wrapper preserving the signature used for dependency injection.
        Context variables propagate; CPU-bound Python still contends for the GIL.
    """
    if inspect.iscoroutinefunction(callback):
        error_msg = "threaded expects a synchronous callable."
        raise TypeError(error_msg)

    @wraps(callback)
    async def invoke(*args: P.args, **kwargs: P.kwargs) -> T:
        """
        Run the decorated operation in the shared callback pool.

        Parameters
        ----------
        *args : P.args
            Positional arguments forwarded to the wrapped operation.
        **kwargs : P.kwargs
            Keyword arguments forwarded to the wrapped operation.

        Returns
        -------
        T
            Result of the wrapped operation.
        """
        return await _CALLBACK_WORKERS.run(callback, *args, **kwargs)

    return invoke
