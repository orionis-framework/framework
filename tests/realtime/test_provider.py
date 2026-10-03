from dataclasses import FrozenInstanceError, asdict
from typing import TYPE_CHECKING, cast
from orionis.container.context.scope import ScopedContext
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.foundation.application import Application
from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
from orionis.foundation.core_config import get_core_config_mapping
from orionis.foundation.core_providers import get_core_providers_mapping
from orionis.realtime.clients import HubClients
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.entities import BroadcastResult
from orionis.realtime.hub import Hub
from orionis.realtime.manager import ConnectionManager
from orionis.realtime.provider import RealtimeProvider
from orionis.support import facades as facade_package
from orionis.support.facades.realtime import Realtime
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication


class _ProviderHub(Hub):
    """Supply an empty namespace without mutating any live registry entries."""

    __slots__ = ()


class _RealtimeConsumer:
    """Request the registry through ordinary constructor injection."""

    __slots__ = ("manager",)

    def __init__(self, manager: IConnectionManager) -> None:
        """
        Capture the container-managed realtime service.

        Parameters
        ----------
        manager : IConnectionManager
            Registry resolved through constructor injection.

        Returns
        -------
        None
            Store the injected registry for identity assertions.
        """
        self.manager = manager


class _ConfigApp:
    """Record provider registration without replacing global application state."""

    __slots__ = ("configured", "instances", "singletons")

    def __init__(self, configured: object = None) -> None:
        """
        Supply one configuration value and empty registration journals.

        Parameters
        ----------
        configured : object, optional
            Configuration entity, mapping or absent value returned to the provider.

        Returns
        -------
        None
            Initialize independently recorded instances and singleton bindings.
        """
        self.configured = configured
        self.instances: dict[type, object] = {}
        self.singletons: list[tuple[type, type]] = []

    def config(self, key: str) -> object:
        """
        Return the selected realtime configuration.

        Parameters
        ----------
        key : str
            Requested configuration namespace.

        Returns
        -------
        object
            Configured realtime value.

        Raises
        ------
        ValueError
            If the requested namespace is not realtime.
        """
        if key != "realtime":
            error_msg = "Provider requested an unexpected configuration namespace"
            raise ValueError(error_msg)
        return self.configured

    def instance(self, abstract: type, instance: object) -> None:
        """
        Record one validated configuration instance.

        Parameters
        ----------
        abstract : type
            Contract under which the instance is registered.
        instance : object
            Validated configuration instance.

        Returns
        -------
        None
            Store the instance under its contract key.
        """
        self.instances[abstract] = instance

    def singleton(self, abstract: type, concrete: type) -> None:
        """
        Record a replaceable singleton manager binding.

        Parameters
        ----------
        abstract : type
            Service contract requested by consumers.
        concrete : type
            Implementation registered for the contract.

        Returns
        -------
        None
            Append the binding to the registration journal.
        """
        self.singletons.append((abstract, concrete))


class TestRealtimeProvider(TestCase):
    """Check eager core wiring and immutable configuration registration."""

    def testCoreDefaultsAndEagerProviderAreRegistered(self) -> None:
        """
        Load realtime through the same core metadata used by Application.

        Returns
        -------
        None
            Verify eager registration and independently constructed defaults.
        """
        self.assertIn(RealtimeProvider, get_core_providers_mapping())
        self.assertFalse(issubclass(RealtimeProvider, DeferrableProvider))
        defaults = get_core_config_mapping()
        self.assertEqual(defaults["realtime"], asdict(RealtimeConfig()))
        defaults["realtime"]["max_groups_per_connection"] = 1
        self.assertEqual(
            get_core_config_mapping()["realtime"]["max_groups_per_connection"], 64,
        )

    def testProviderPreservesEntitiesAndValidatesConfigurationMappings(self) -> None:
        """
        Register exactly one manager contract and one typed configuration.

        Returns
        -------
        None
            Verify entity preservation, mapping validation and frozen options.
        """
        configured = RealtimeConfig(broadcast_concurrency=3)
        for raw in (configured, {"broadcast_concurrency": 3}, None):
            with self.subTest(raw=raw):
                app = _ConfigApp(raw)
                RealtimeProvider(cast("IApplication", app)).register()
                self.assertEqual(
                    app.singletons, [(IConnectionManager, ConnectionManager)],
                )
                config = cast("RealtimeConfig", app.instances[RealtimeConfig])
                self.assertIsInstance(config, RealtimeConfig)
                if raw is configured:
                    self.assertIs(config, configured)
                elif raw is not None:
                    self.assertEqual(config.broadcast_concurrency, 3)
                for field in ("broadcast_concurrency", "max_groups_per_connection"):
                    with self.assertRaises(FrozenInstanceError):
                        setattr(config, field, 10)
        invalid = _ConfigApp({"max_concurrent_invocations": 0})
        with self.assertRaises(ValueError):
            RealtimeProvider(cast("IApplication", invalid)).register()
        self.assertEqual(invalid.instances, {})
        self.assertEqual(invalid.singletons, [])


class TestRealtimeFacade(TestCase):
    """Use the already booted application's facade without mutating its pin."""

    def setUp(self) -> None:
        """
        Keep singleton assertions outside the runner's ambient scope.

        Returns
        -------
        None
            Save the ambient scope token and temporarily clear the scope.
        """
        self._scope_token = ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """
        Restore the existing application scope after read-only resolutions.

        Returns
        -------
        None
            Reset the original ambient scope using its saved token.
        """
        ScopedContext.reset(self._scope_token)

    async def testFacadeAndInjectionShareTheApplicationManager(self) -> None:
        """
        Resolve one registry through all supported application entry points.

        Returns
        -------
        None
            Verify facade, constructor injection and scoped singleton identity.
        """
        app = Application()
        manager = await app.make(IConnectionManager)
        consumer = await app.build(_RealtimeConsumer)
        self.assertIsInstance(manager, ConnectionManager)
        self.assertIs(consumer.manager, manager)
        self.assertIs(await Realtime.resolve(), manager)
        async with app.beginScope():
            self.assertIs(await app.make(IConnectionManager), manager)
        clients = Realtime.hub(_ProviderHub)
        self.assertIsInstance(clients, HubClients)
        self.assertIs(clients._manager, manager)
        self.assertEqual(await clients.all.send("notice"), BroadcastResult())
        self.assertIs(facade_package.Realtime, Realtime)
        self.assertIs(Realtime.getFacadeAccessor(), IConnectionManager)
