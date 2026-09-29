from orionis.console.base import BaseScheduler
from orionis.console.contracts import ISchedule
from orionis.console.entities import SchedulerEvent

class Scheduler(BaseScheduler):

    def tasks(
        self,
        schedule: ISchedule,
    ) -> None:
        """
        Register scheduled tasks for the application.

        Set up tasks that the scheduler will execute using the provided schedule
        object.

        Parameters
        ----------
        schedule : ISchedule [Dependency Injection]
            The schedule object used to register scheduled commands.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Register a test command that runs every ten seconds
        schedule.command("app:test", ["--name=Raul"])\
            .purpose("Test Route Command")\
            .maxInstances(1)\
            .everyTenSeconds()

        # Register the inspire command to run every fifteen seconds with a listener
        schedule.command("app:inspire")\
            .purpose("Test Inspire Command")\
            .maxInstances(1)\
            .everySeconds(15)

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
        await super().onStarted(event)

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
        await super().onPaused(event)

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
        await super().onResumed(event)

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
        await super().onShutdown(event)
