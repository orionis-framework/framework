from orionis.console.contracts.schedule import ISchedule
from orionis.container.facades.facade import Facade

class Schedule(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the facade accessor string for the unit test contract.

        Returns
        -------
        str
            String identifier for the service in the application container.
        """
        return ISchedule
