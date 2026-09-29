from orionis.console.base.contracts.listener import IBaseTaskListener
from orionis.console.output.console import Console
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.console.entities.task_event import TaskEvent

class BaseTaskListener(Console, IBaseTaskListener):

    async def onTaskAdded(self, event: TaskEvent) -> None:
        """
        Handle the event when a task is added.

        Parameters
        ----------
        event : TaskEvent
            The event object containing information about the added task.

        Returns
        -------
        None
            This method does not return a value.
        """

    async def onTaskRemoved(self, event: TaskEvent) -> None:
        """
        Handle the event when a task is removed.

        Parameters
        ----------
        event : TaskEvent
            The event object containing information about the removed task.

        Returns
        -------
        None
            This method does not return a value.
        """

    async def onTaskExecuted(self, event: TaskEvent) -> None:
        """
        Handle the event when a task is executed.

        Parameters
        ----------
        event : TaskEvent
            The event object containing information about the executed task.

        Returns
        -------
        None
            This method does not return a value.
        """

    async def onTaskError(self, event: TaskEvent) -> None:
        """
        Handle the event when a task encounters an error.

        Parameters
        ----------
        event : TaskEvent
            The event object containing information about the task error.

        Returns
        -------
        None
            This method does not return a value.
        """

    async def onTaskMissed(self, event: TaskEvent) -> None:
        """
        Handle the event when a task is missed.

        Parameters
        ----------
        event : TaskEvent
            The event object containing information about the missed task.

        Returns
        -------
        None
            This method does not return a value.
        """

    async def onTaskSubmitted(self, event: TaskEvent) -> None:
        """
        Handle the event when a task is submitted.

        Parameters
        ----------
        event : TaskEvent
            The event object containing information about the submitted task.

        Returns
        -------
        None
            This method does not return a value.
        """

    async def onTaskMaxInstances(self, event: TaskEvent) -> None:
        """
        Handle the event when a task reaches its maximum allowed instances.

        Parameters
        ----------
        event : TaskEvent
            The event object containing information about the max instances event.

        Returns
        -------
        None
            This method does not return a value.
        """
