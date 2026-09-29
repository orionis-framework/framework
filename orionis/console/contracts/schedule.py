from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Self, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.console.enums.events import SchedulerEvent
    from orionis.console.fluent.contracts.task import ITask

class ISchedule(ABC):

    @abstractmethod
    async def info(self) -> list[dict]:
        """
        Retrieve information about all loaded fluent tasks.

        Returns
        -------
        list of dict
            A list of dictionaries, each containing details about a loaded task.
        """

    @abstractmethod
    async def boot(self) -> None:
        """
        Boot the scheduler and register all configured tasks.

        Load available command signatures, validate and load fluent tasks,
        initialize the scheduler, register event listeners, and add all jobs
        to the scheduler.

        Returns
        -------
        None
            This method does not return a value but initializes the scheduler.
        """

    @abstractmethod
    def on(
        self,
        event: SchedulerEvent,
        listener: Callable,
    ) -> Self:
        """
        Register a listener for a scheduler event.

        Parameters
        ----------
        event : SchedulerEvent
            The scheduler event to listen for.
        listener : Callable
            The callable to invoke when the event occurs.

        Returns
        -------
        Self
            The Schedule instance for method chaining.

        Raises
        ------
        RuntimeError
            If the scheduler has already been booted.
        TypeError
            If event is not a SchedulerEvent or listener is not callable.
        """

    @abstractmethod
    def state(self) -> str:
        """
        Return the current scheduler state as a string.

        Returns
        -------
        str
            The current state of the scheduler, e.g., "RUNNING", "PAUSED", or "STOPPED".
        """

    @abstractmethod
    def isRunning(self) -> bool:
        """
        Determine if the scheduler is currently running.

        Returns
        -------
        bool
            True if the scheduler state is "RUNNING", otherwise False.
        """

    @abstractmethod
    def isPaused(self) -> bool:
        """
        Determine if the scheduler is currently paused.

        Returns
        -------
        bool
            True if the scheduler state is "PAUSED", otherwise False.
        """

    @abstractmethod
    def isStopped(self) -> bool:
        """
        Determine if the scheduler is currently stopped.

        Returns
        -------
        bool
            True if the scheduler state is "STOPPED", otherwise False.
        """

    @abstractmethod
    def command(
        self,
        signature: str,
        args: list[str] | None = None,
        purpose: str | None = None,
    ) -> ITask:
        """
        Add a command for fluent configuration.

        Parameters
        ----------
        signature : str
            Unique signature of the command to schedule.
        args : list[str] | None, optional
            Arguments for the command. Defaults to None.
        purpose : str | None, optional
            Description of the command's purpose.

        Returns
        -------
        ITask
            Task instance for further configuration.

        Raises
        ------
        RuntimeError
            If the scheduler has already been started.
        TypeError
            If the signature is not a non-empty string or arguments are invalid.
        """

    @abstractmethod
    def pauseTask(
        self,
        signature: str,
    ) -> bool:
        """
        Pause a running task by its signature.

        Parameters
        ----------
        signature : str
            Unique identifier of the task to pause.

        Returns
        -------
        bool
            True if the task was successfully paused, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or the task is not running.
        ValueError
            If the specified task does not exist.

        Notes
        -----
        This method pauses a running task in the scheduler.
        """

    @abstractmethod
    def resumeTask(
        self,
        signature: str,
    ) -> bool:
        """
        Resume a paused task by its signature.

        Parameters
        ----------
        signature : str
            Unique identifier of the task to resume.

        Returns
        -------
        bool
            True if the task was successfully resumed, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or the task is not paused.
        ValueError
            If the specified task does not exist.

        Notes
        -----
        This method resumes a paused task in the scheduler.
        """

    @abstractmethod
    def removeTask(
        self,
        signature: str,
    ) -> bool:
        """
        Remove a task from the scheduler by its signature.

        Parameters
        ----------
        signature : str
            Unique identifier of the task to remove.

        Returns
        -------
        bool
            True if the task was successfully removed, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or the task is not found.
        ValueError
            If the specified task does not exist.

        Notes
        -----
        This method removes a task from the scheduler and updates internal state.
        """

    @abstractmethod
    def removeAllTasks(self) -> bool:
        """
        Remove all tasks from the scheduler.

        Returns
        -------
        bool
            True if all tasks were successfully removed, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or an error occurs during removal.

        Notes
        -----
        This method removes all tasks from the scheduler and updates internal state.
        """

    @abstractmethod
    def pause(self) -> bool:
        """
        Pause the scheduler if it is running.

        Parameters
        ----------
        self : Schedule
            The Schedule instance.

        Returns
        -------
        bool
            True if the scheduler was successfully paused.

        Raises
        ------
        RuntimeError
            If the scheduler is not started or not running.
        """

    @abstractmethod
    def resume(self) -> bool:
        """
        Resume the scheduler if it is paused.

        Parameters
        ----------
        self : Schedule
            The Schedule instance.

        Returns
        -------
        bool
            True if the scheduler was successfully resumed.

        Raises
        ------
        RuntimeError
            If the scheduler is not started or not paused.
        """

    @abstractmethod
    def shutdown(self, wait: int | None = None) -> None:
        """
        Shut down the task scheduler safely without waiting for running tasks.

        This method terminates the scheduler execution safely. It does not wait
        for currently executing tasks to complete, but prevents new tasks from
        starting and cleans up scheduler resources. Ideal for console
        environments where the process stops immediately after calling this
        method.

        Parameters
        ----------
        wait : int | None, optional
            Time in seconds to wait before completing shutdown. Defaults to None.

        Returns
        -------
        None
            This method does not return a value. It initiates graceful shutdown.
        """

    @abstractmethod
    async def wait(self) -> None:
        """
        Wait for the scheduler shutdown to complete.

        This method blocks until the shutdown process initiated by the shutdown()
        method has finished. It provides a way to synchronize with the graceful
        shutdown process.

        Returns
        -------
        None
            This method does not return a value but blocks until shutdown
            completes.
        """
