# ruff: noqa: PT009, PT027, S603, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Run fixed cold-import probes through the selected interpreter without a shell.
import subprocess
import sys
from dataclasses import FrozenInstanceError, asdict
from inspect import isfunction
from typing import TYPE_CHECKING, cast
from typing import get_type_hints
from orionis.realtime.clients import ClientTarget
from orionis.realtime.connection import RealtimeConnection
from orionis.realtime.contracts.connection import RealtimeConnectionLike
from orionis.realtime.decorators import remote
from orionis.realtime.groups import HubGroups
from orionis.container.context.scope import ScopedContext
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.foundation.application import Application
from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
from orionis.foundation.core_config import get_core_config_mapping
from orionis.foundation.core_providers import get_core_providers_mapping
from orionis.realtime.clients import HubClients
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.entities import BroadcastResult
from orionis.realtime.hub import Hub, HubContext
from orionis.realtime.manager import ConnectionManager
from orionis.realtime.provider import RealtimeProvider
from orionis.realtime.protocol import HubProtocol
from orionis.realtime.runtime import HubRuntime
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
            get_core_config_mapping()["realtime"]["max_groups_per_connection"],
            64,
        )

    def testPublicRuntimeAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """Resolve public protocols, factories and context fields in isolation.

        Returns
        -------
        None
            No return value.
        """
        for owner in (
            Hub,
            HubContext,
            HubClients,
            ClientTarget,
            HubGroups,
            HubProtocol,
            RealtimeConnection,
            RealtimeConnectionLike,
            ConnectionManager,
            IConnectionManager,
            HubRuntime,
        ):
            with self.subTest(owner=owner.__name__):
                get_type_hints(owner)
            for name, member in vars(owner).items():
                method = (
                    member.__func__
                    if isinstance(member, (classmethod, staticmethod))
                    else member.fget
                    if isinstance(member, property)
                    else member
                )
                if isfunction(method) and name != "__annotate_func__":
                    with self.subTest(owner=owner.__name__, method=name):
                        get_type_hints(method)
        get_type_hints(remote)

    def testFalsyInvalidConfigurationCannotRegisterDefaults(self) -> None:
        """Reject invalid configuration even when its value is falsy.

        Returns
        -------
        None
            No return value.
        """
        for raw in (False, 0, [], "", ()):
            app = _ConfigApp(raw)
            with self.subTest(value=raw):
                with self.assertRaises(TypeError):
                    RealtimeProvider(cast("IApplication", app)).register()
                self.assertEqual(app.instances, {})
                self.assertEqual(app.singletons, [])

    def testRuntimeTypesSurviveIndependentColdImportOrders(self) -> None:
        """Resolve cyclic protocol annotations after each supported import entry.

        Returns
        -------
        None
            No return value.
        """
        source = """
import importlib
import sys
from typing import get_type_hints
importlib.import_module(sys.argv[1])
from orionis.realtime import Hub, HubContext, HubClients, HubGroups
from orionis.realtime.contracts.connection import RealtimeConnectionLike
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.connection import RealtimeConnection
from orionis.realtime.runtime import HubRuntime
for target in (
    Hub, HubContext, HubContext.__init__, HubClients.__init__, HubGroups.__init__,
    RealtimeConnectionLike.context.fget, RealtimeConnectionLike.hub.fget,
    IConnectionManager.hub, RealtimeConnection.__init__, HubRuntime.__init__,
):
    assert get_type_hints(target)
assert get_type_hints(Hub)["clients"] is HubClients
assert get_type_hints(IConnectionManager.hub)["return"] is HubClients
print("realtime runtime annotations resolved")
"""
        for module in (
            "orionis.realtime.hub",
            "orionis.realtime.clients",
            "orionis.realtime.groups",
            "orionis.realtime.contracts.connection",
            "orionis.realtime.contracts.manager",
            "orionis.realtime.connection",
            "orionis.realtime.runtime",
            "orionis.realtime.metadata",
        ):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", source, module],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("realtime runtime annotations resolved", result.stdout)

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
                    app.singletons,
                    [(IConnectionManager, ConnectionManager)],
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
