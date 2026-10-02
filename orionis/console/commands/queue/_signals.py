import asyncio
import signal
from contextlib import suppress
from functools import partial
from threading import current_thread, main_thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType
    from orionis.queues.contracts.worker import IWorker


def _stop_worker(worker: IWorker, _signal: int, _frame: FrameType | None) -> None:
    """Request graceful draining after a process termination signal.

    Parameters
    ----------
    worker : IWorker
        Active worker that should stop reserving jobs.
    _signal : int
        Delivered process signal.
    _frame : FrameType | None
        Interrupted interpreter frame.
    """
    worker.stop()


class WorkerSignals:
    """Install temporary worker shutdown handlers on the main thread."""

    __slots__ = ("_handlers", "_loop", "_worker")

    def __init__(self, worker: IWorker) -> None:
        """Store the worker and currently running event loop.

        Parameters
        ----------
        worker : IWorker
            Worker receiving graceful shutdown requests.
        """
        self._worker = worker
        self._loop = asyncio.get_running_loop()
        self._handlers: dict[int, object] = {}

    def __enter__(self) -> None:
        """Install portable signal callbacks without replacing thread handlers."""
        if current_thread() is not main_thread():
            return
        for signum in (signal.SIGINT, signal.SIGTERM):
            self._handlers[signum] = signal.getsignal(signum)
            try:
                self._loop.add_signal_handler(signum, self._worker.stop)
            except NotImplementedError:
                signal.signal(signum, partial(_stop_worker, self._worker))

    def __exit__(self, *_exception: object) -> None:
        """Restore the application's previous signal handlers.

        Parameters
        ----------
        _exception : object
            Exception details from the context manager.
        """
        for signum, handler in self._handlers.items():
            with suppress(NotImplementedError):
                self._loop.remove_signal_handler(signum)
            signal.signal(signum, handler)
