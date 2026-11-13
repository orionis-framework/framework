"""Resolve the test service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.test.contracts.engine import ITestingEngine


class Test(Facade):
    """Resolve the test service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the contract used to resolve the test engine.

        Returns
        -------
        type[ITestingEngine]
            Contract registered in the application container.
        """
        return ITestingEngine
