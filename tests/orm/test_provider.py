from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.orm import provider as provider_module
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.provider import QueryBuilderProvider
from orionis.orm.query_builder import QueryBuilder
from orionis.test import TestCase

class _CaptureApp:
    """Record the provider's service registrations."""

    __slots__ = ("bindings",)

    def __init__(self) -> None:
        """Initialize an independent registration log.

        Returns
        -------
        None
            Prepare the current test's container observations.
        """
        self.bindings: list[tuple[type, type]] = []

    def singleton(self, contract: type, implementation: type) -> None:
        """Record the singleton requested by the provider.

        Parameters
        ----------
        contract : type
            Container binding key.
        implementation : type
            Concrete service to construct.

        Returns
        -------
        None
            Append the requested registration.
        """
        self.bindings.append((contract, implementation))

class _RecordingFacade:
    """Record facade pinning without touching the running application's DB."""

    __slots__ = ("pin_count",)

    def __init__(self) -> None:
        """Initialize the facade boot observations.

        Returns
        -------
        None
            Start the pin counter at zero.
        """
        self.pin_count = 0

    async def pin(self) -> None:
        """Record the provider's awaited pin operation.

        Returns
        -------
        None
            Increment the facade pin counter.
        """
        self.pin_count += 1

class TestQueryBuilderProvider(TestCase):
    """Verify singleton registration and eager facade boot wiring."""

    def setUp(self) -> None:
        """Install an isolated facade double for provider boot.

        Returns
        -------
        None
            Preserve the real facade and prepare provider observations.
        """
        self.app = _CaptureApp()
        self.facade = _RecordingFacade()
        self.addCleanup(setattr, provider_module, "DB", provider_module.DB)
        provider_module.DB = self.facade
        self.provider = QueryBuilderProvider(self.app)  # type: ignore[arg-type]

    def testRegisterBindsGatewayAsSingleton(self) -> None:
        """Register the gateway under the public query builder contract.

        Returns
        -------
        None
            Verify the provider declares exactly one singleton binding.
        """
        self.provider.register()
        self.assertEqual(self.app.bindings, [(IQueryBuilder, QueryBuilder)])
        self.assertEqual(self.facade.pin_count, 0)

    async def testBootPinsTheFacade(self) -> None:
        """Pin the facade without adding registrations during boot.

        Returns
        -------
        None
            Verify boot awaits one pin operation and leaves bindings unchanged.
        """
        await self.provider.boot()
        self.assertEqual(self.facade.pin_count, 1)
        self.assertEqual(self.app.bindings, [])

    def testProviderIsEagerAndRegisteredInTheCore(self) -> None:
        """Keep the gateway available during ordinary application startup.

        Returns
        -------
        None
            Verify core registration and the non-deferrable provider lifetime.
        """
        self.assertIn(QueryBuilderProvider, CORE_PROVIDERS)
        self.assertFalse(issubclass(QueryBuilderProvider, DeferrableProvider))
