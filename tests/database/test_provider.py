# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
from unittest.mock import AsyncMock, Mock, patch
from orionis.container.providers.service_provider import ServiceProvider
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.provider import ConnectionManagerProvider
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.support.facades.db import DB
from orionis.test import TestCase


class _CaptureApp:
    """Application stub capturing singleton registrations."""

    def __init__(self) -> None:
        """Initialize the test double.

        Returns
        -------
        None
            No return value.
        """
        self.bindings: list[tuple[type, type]] = []

    def singleton(self, contract: type, implementation: type) -> None:
        """Record a singleton service registration.

        Parameters
        ----------
        contract : type
            Value supplied for ``contract``.
        implementation : type
            Value supplied for ``implementation``.

        Returns
        -------
        None
            No return value.
        """
        self.bindings.append((contract, implementation))


class TestConnectionManagerProvider(TestCase):
    """Registration and boot wiring of the connection manager provider."""

    def testProviderInheritsFrameworkBase(self) -> None:
        """Extend the framework ServiceProvider base.

        Validates the provider class hierarchy.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(ConnectionManagerProvider, ServiceProvider))

    def testRegisterBindsManagerAsSingleton(self) -> None:
        """Bind IConnectionManager as a singleton.

        Validates the container registration.

        Returns
        -------
        None
            No return value.
        """
        app = _CaptureApp()
        provider = ConnectionManagerProvider(app)  # type: ignore[arg-type]
        provider.register()
        self.assertEqual(app.bindings, [(IConnectionManager, ConnectionManager)])

    async def testBootInstallsManagerOnResolver(self) -> None:
        """Install the resolved manager on the ORM resolver.

        Validates that models reach connections without the container.

        Returns
        -------
        None
            No return value.
        """
        with patch.object(ConnectionResolver, "_manager", None):
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


class TestDBFacade(TestCase):
    """Contract exposed by the DB facade."""

    def testFacadeAccessorIsGatewayContract(self) -> None:
        """Expose IQueryBuilder as the facade accessor.

        Validates the facade to container binding.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(DB.getFacadeAccessor(), IQueryBuilder)
