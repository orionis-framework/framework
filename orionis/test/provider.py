from __future__ import annotations
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.testing import Test as TestFacade
from orionis.test.contracts.engine import ITestingEngine

class TestingProvider(ServiceProvider, DeferrableProvider):

    # ruff: noqa: PLC0415

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
        Bind the deferred testing engine as a singleton.

        Returns
        -------
        None
            Register the engine implementation under its contract.
        """
        from orionis.test.core.engine import TestingEngine
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
