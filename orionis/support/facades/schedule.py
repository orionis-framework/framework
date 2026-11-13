"""Resolve the schedule service through the application facade."""

from orionis.console.contracts.schedule import ISchedule
from orionis.container.facades.facade import Facade


class Schedule(Facade):
    """Resolve the schedule service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the contract used to resolve the scheduler.

        Returns
        -------
        type[ISchedule]
            Contract registered in the application container.
        """
        return ISchedule
