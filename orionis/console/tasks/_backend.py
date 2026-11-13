# ruff: noqa: BLE001, FBT001, FBT002
# Retain APScheduler's positional boolean contract and transfer failures across threads.
"""Own APScheduler 3 shutdown callbacks and their asynchronous jobs."""

from __future__ import annotations
import asyncio
from concurrent.futures import Future
from typing import TYPE_CHECKING
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers import SchedulerNotRunningError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import BaseScheduler
from orionis.failure.runtime import capture_nowait

if TYPE_CHECKING:
    from datetime import tzinfo


class _Executor(AsyncIOExecutor):
    """Expose the futures owned by the native asyncio executor."""

    def __init__(self) -> None:
        """
        Initialize future tracking before native startup can fail.

        Returns
        -------
        None
            No return value.
        """
        super().__init__()
        self._pending_futures = set()
        """Native job futures retained even if executor startup fails."""

    def pendingTasks(self) -> tuple[asyncio.Future[object], ...]:
        """
        Snapshot submitted futures before native shutdown clears its registry.

        Returns
        -------
        tuple of asyncio.Future
            Futures whose cancellation cleanup remains owned by the scheduler.
        """
        return tuple(self._pending_futures)


class SchedulerBackend(AsyncIOScheduler):
    """Bridge native loop callbacks to the framework's awaited shutdown."""

    def __init__(
        self,
        *,
        event_loop: asyncio.AbstractEventLoop,
        timezone: tzinfo,
    ) -> None:
        """
        Retain the native executor and its shutdown snapshot.

        Parameters
        ----------
        event_loop : asyncio.AbstractEventLoop
            Loop owning scheduled jobs and native shutdown.
        timezone : datetime.tzinfo
            Timezone used by the scheduler.

        Returns
        -------
        None
            No return value.
        """
        self.__executor: _Executor | None = None
        """Native executor whose futures must outlive cancellation requests."""
        self.__pending: tuple[asyncio.Future[object], ...] = ()
        """Job futures awaiting transfer to the framework's shutdown owner."""
        super().__init__(event_loop=event_loop, timezone=timezone)

    def _createDefaultExecutor(self) -> _Executor:
        """
        Create the executor through APScheduler's required extension hook.

        Returns
        -------
        _Executor
            Executor retaining the native future registry.
        """
        self.__executor = _Executor()
        return self.__executor

    # APScheduler requires this external hook name.
    _create_default_executor = _createDefaultExecutor

    def takePending(self) -> tuple[asyncio.Future[object], ...]:
        """
        Transfer pending job cleanup to the framework shutdown owner.

        Returns
        -------
        tuple of asyncio.Future
            Previously captured futures, released from this backend's snapshot.
        """
        pending, self.__pending = self.__pending, ()
        return pending

    def shutdown(self, wait: bool = True) -> None:
        """
        Finish native shutdown before returning to a waiting worker thread.

        Parameters
        ----------
        wait : bool, default True
            Native executor shutdown option.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        SchedulerNotRunningError
            If no owning loop remains.
        BaseException
            If native shutdown fails, preserving the original exception.
        """
        loop = self._eventloop
        if loop is None:
            raise SchedulerNotRunningError
        if not loop.is_running():
            error_msg = "The scheduler event loop is not running."
            raise RuntimeError(error_msg)
        try:
            current = asyncio.get_running_loop()
        except RuntimeError:
            current = None
        if current is loop:
            self.__shutdownOnLoop(wait=wait)
            return

        completion: Future[None] = Future()

        def finish() -> None:
            """
            Deliver native completion or failure to the waiting worker.

            Returns
            -------
            None
                No return value.
            """
            try:
                self.__shutdownOnLoop(wait=wait)
            except BaseException as error:  # NOSONAR(S5754)
                # completion.result() re-raises this same object in the caller.
                completion.set_exception(error)
            else:
                completion.set_result(None)

        loop.call_soon_threadsafe(finish)
        completion.result()

    def __shutdownOnLoop(self, *, wait: bool) -> None:
        """
        Run shutdown on the owning loop and always retire its timer.

        Parameters
        ----------
        wait : bool
            Native executor shutdown option.

        Returns
        -------
        None
            No return value.
        """
        if self.__executor is not None:
            self.__pending = self.__executor.pendingTasks()
        try:
            BaseScheduler.shutdown(self, wait=wait)
        finally:
            self._stop_timer()
            self._eventloop = None
            """Retired owner loop after native shutdown, including failures."""

    def abortStart(self, primary: BaseException) -> None:
        """
        Release owned stores and executors after partial startup.

        Parameters
        ----------
        primary : BaseException
            Startup failure retained while cleanup failures are observed.

        Returns
        -------
        None
            No return value.
        """
        if self.__executor is not None:
            self.__pending = self.__executor.pendingTasks()
        for aliases, remove in (
            (tuple(self._executors), self.remove_executor),
            (tuple(self._jobstores), self.remove_jobstore),
        ):
            for alias in aliases:
                try:
                    remove(alias, shutdown=True)
                except BaseException as error:  # NOSONAR(S5754)
                    # Keep the primary failure while recording every cleanup error.
                    primary.add_note(f"Scheduler startup cleanup also failed: {error}")
                    capture_nowait(error, flow="scheduler", phase="startup_cleanup")
        self._stop_timer()
        self._eventloop = None
