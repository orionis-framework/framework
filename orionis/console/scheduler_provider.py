from orionis.console.contracts.schedule import ISchedule
from orionis.console.contracts.store import IScheduleStore
from orionis.console.tasks.schedule import Schedule
from orionis.console.tasks.store import ScheduleStore
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.schedule import Schedule as ScheduleFacade

class ScheduleProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the Scheduler as a singleton service in the application container.

        Binds the `ISchedule` interface to the `Schedule` implementation, ensuring a
        single instance throughout the application's lifecycle. Also binds
        `IScheduleStore` to `ScheduleStore` so it can be auto-resolved as a
        constructor dependency of `Schedule`.

        Parameters
        ----------
        None

        Returns
        -------
        None
            This method performs registration as a side effect and returns None.
        """
        self.app.singleton(IScheduleStore, ScheduleStore)
        self.app.singleton(ISchedule, Schedule)

    async def boot(self) -> None:
        """
        Initialize the Schedule facade asynchronously during the boot process.

        This method ensures that the Schedule facade is properly initialized before
        handling requests.

        Returns
        -------
        None
            This method does not return a value.
        """
        await ScheduleFacade.pin()
