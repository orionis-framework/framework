from __future__ import annotations
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.testing import Test as TestFacade
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.core.engine import TestingEngine

class TestingProvider(ServiceProvider, DeferrableProvider):

    @classmethod
    def provides(cls) -> list[type]:
        """
        Return the list of services provided by this provider.

        Returns
        -------
        list[type[ITestingEngine]]
            A list containing the ITestingEngine interface that this provider
            registers.
        """
        return [ITestingEngine]

    def register(self) -> None:
        """
        Register the unit testing service in the application container.

        Retrieves the application's testing configuration, creates a UnitTest
        service instance, and registers it as a singleton in the dependency
        injection container. The service is bound to the ITestingEngine interface.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.app.singleton(ITestingEngine, TestingEngine)

    async def boot(self) -> None:
        """
        Initialize the testing facade asynchronously.

        Prepares the testing environment by initializing the TestFacade.

        Returns
        -------
        None
            This method does not return a value.
        """
        await TestFacade.pin()
