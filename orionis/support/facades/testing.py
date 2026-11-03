"""Resolve the test service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.test.contracts.engine import ITestingEngine

class Test(Facade):
    """Resolve the test service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the facade accessor string for the unit test contract.

        Returns
        -------
        str
            String identifier for the service in the application container.
        """
        return ITestingEngine
