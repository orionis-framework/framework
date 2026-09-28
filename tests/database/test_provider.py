from __future__ import annotations
from unittest.mock import AsyncMock, Mock, patch
from orionis.container.providers.service_provider import ServiceProvider
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.provider import ConnectionManagerProvider
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.contracts.raw_builder import IRawQueryBuilder
from orionis.orm.provider import QueryBuilderProvider
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.support.facades.db import DB
from orionis.test import TestCase


class _CaptureApp:
    """Application stub capturing singleton registrations."""

    def __init__(self) -> None:
        self.bindings: list[tuple[type, type]] = []

    def singleton(self, contract: type, implementation: type) -> None:
        self.bindings.append((contract, implementation))


class TestConnectionManagerProvider(TestCase):
    """Registration and boot wiring of the connection manager provider."""

    def testProviderInheritsFrameworkBase(self) -> None:
        """
        Extend the framework ServiceProvider base.

        Validates the provider class hierarchy.
        """
        self.assertTrue(issubclass(ConnectionManagerProvider, ServiceProvider))

    def testRegisterBindsManagerAsSingleton(self) -> None:
        """
        Bind IConnectionManager as a singleton.

        Validates the container registration.
        """
        app = _CaptureApp()
        provider = ConnectionManagerProvider(app)  # type: ignore[arg-type]
        provider.register()
        self.assertEqual(app.bindings, [(IConnectionManager, ConnectionManager)])

    async def testBootInstallsManagerOnResolver(self) -> None:
        """
        Install the resolved manager on the ORM resolver.

        Validates that models reach connections without the container.
        """
        previous = ConnectionResolver._manager
        try:
            application = Mock()
            application.config.return_value = {
                "default": "sqlite",
                "connections": {"sqlite": {"driver": "sqlite"}},
            }
            manager = ConnectionManager(application)
            application.make = AsyncMock(return_value=manager)
            provider = ConnectionManagerProvider(application)
            await provider.boot()
            application.make.assert_awaited_once_with(IConnectionManager)
            self.assertIs(ConnectionResolver.manager(), manager)
        finally:
            ConnectionResolver._manager = previous


class TestQueryBuilderProvider(TestCase):
    """Registration and boot wiring of the query builder gateway."""

    def testRegisterBindsGatewayAsSingleton(self) -> None:
        """
        Bind IQueryBuilder as a singleton.

        Validates the container registration.
        """
        app = _CaptureApp()
        provider = QueryBuilderProvider(app)  # type: ignore[arg-type]
        provider.register()
        self.assertEqual(app.bindings, [(IQueryBuilder, QueryBuilder)])

    async def testBootPinsTheFacade(self) -> None:
        """
        Pin the DB facade so it resolves without awaiting a dispatcher.

        Validates the boot wiring against the booted application.
        """
        gateway = QueryBuilder(db_manager=None)
        application = Mock(isBooted=True)
        application.make = AsyncMock(return_value=gateway)
        with (
            patch.object(DB, "_application", application),
            patch.object(DB, "_pinned_instance", None),
        ):
            await QueryBuilderProvider(application).boot()
            application.make.assert_awaited_once_with(IQueryBuilder)
            self.assertIs(DB._pinned_instance, gateway)
            self.assertIsInstance(DB.table("users"), IRawQueryBuilder)


class TestDBFacade(TestCase):
    """Contract exposed by the DB facade."""

    def testFacadeAccessorIsGatewayContract(self) -> None:
        """
        Expose IQueryBuilder as the facade accessor.

        Validates the facade to container binding.
        """
        self.assertIs(DB.getFacadeAccessor(), IQueryBuilder)


class TestQueryBuilderGateway(TestCase):
    """Statelessness guarantees of the singleton gateway."""

    def setUp(self) -> None:
        """Build a gateway over a stub manager."""
        self._gateway = QueryBuilder(db_manager=None)  # type: ignore[arg-type]

    def testTableReturnsIndependentBuilders(self) -> None:
        """
        Build a fresh builder on every table() call.

        Validates that concurrent callers never share query state.
        """
        first = self._gateway.table("users")
        second = self._gateway.table("posts")
        self.assertIsNot(first, second)
        self.assertIsNot(first.toPlan(), second.toPlan())

    def testConnectionReturnsScopedGatewayWithoutMutating(self) -> None:
        """
        Scope a gateway to a connection without mutating the singleton.

        Validates that ``DB.connection(...)`` cannot retarget the shared
        instance every other caller resolves.
        """
        scoped = self._gateway.connection("reporting")
        self.assertIsNot(scoped, self._gateway)
        self.assertIsNone(self._gateway.table("users")._connection_name)
        self.assertEqual(scoped.table("users")._connection_name, "reporting")

    def testTableConnectionOverridesGatewayScope(self) -> None:
        """
        Honor the per-call connection argument declared by the contract.

        Validates that the explicit argument wins over the gateway scope.
        """
        scoped = self._gateway.connection("reporting")
        builder = scoped.table("users", connection="analytics")
        self.assertEqual(builder._connection_name, "analytics")
