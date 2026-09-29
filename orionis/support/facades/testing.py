from orionis.container.facades.facade import Facade
from orionis.test.contracts.engine import ITestingEngine

class Test(Facade):

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
