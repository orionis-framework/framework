from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.console.contracts.schedule import ISchedule
    from orionis.console.entities.scheduler_event import SchedulerEvent

class IBaseScheduler(ABC):

    @abstractmethod
    async def tasks(self, schedule: ISchedule) -> None:
        """
        Register scheduled tasks for the application.

        This method sets up tasks that the scheduler will execute using the provided
        `schedule` object. Subclasses should override this method to define specific
        tasks and their scheduling properties.

        Parameters
        ----------
        schedule : ISchedule
            The schedule object used to register scheduled commands.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Subclasses must implement this method to specify their task scheduling logic.
        """
        error_msg = (
            "Subclasses must implement the 'tasks' method to register scheduled tasks."
        )
        raise NotImplementedError(error_msg)

    @abstractmethod
    async def onStarted(self, event: SchedulerEvent) -> None:
        """
        Handle the scheduler start event.

        Parameters
        ----------
        event : SchedulerEvent
            The event object representing the scheduler start.

        Returns
        -------
        None
            This method does not return any value.
        """

    @abstractmethod
    async def onPaused(self, event: SchedulerEvent) -> None:
        """
        Handle the scheduler pause event.

        Parameters
        ----------
        event : SchedulerEvent
            The event object representing the scheduler pause.

        Returns
        -------
        None
            This method does not return any value.
        """

    @abstractmethod
    async def onResumed(self, event: SchedulerEvent) -> None:
        """
        Handle the scheduler resumption event.

        Parameters
        ----------
        event : SchedulerEvent
            The event object representing the scheduler resumption.

        Returns
        -------
        None
            This method does not return any value.
        """

    @abstractmethod
    async def onShutdown(self, event: SchedulerEvent) -> None:
        """
        Handle the scheduler finalization event.

        Parameters
        ----------
        event : SchedulerEvent
            The event object representing the scheduler shutdown.

        Returns
        -------
        None
            This method does not return any value.
        """
