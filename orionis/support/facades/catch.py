"""Resolve the catch service through the application facade."""

from orionis.container.facades.facade import Facade

class Catch(Facade):
    """Resolve the catch service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """
        Return the facade accessor string for the unit test contract.

        Returns
        -------
        str
            String identifier for the service in the application container.
        """
        return "x-orionis-ICatch"
