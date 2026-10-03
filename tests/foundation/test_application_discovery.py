from __future__ import annotations
import sys
import unittest
from abc import abstractmethod
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.application import Application

def make_application() -> Application:
    """Create an isolated application with initialized container state.

    Returns
    -------
    Application
        Application independent of the process singleton.
    """
    app = object.__new__(Application)
    Application.__init__(app)
    return app

def abstract_registration(_self: ServiceProvider) -> None:
    """Declare an abstract provider registration method.

    Parameters
    ----------
    _self : ServiceProvider
        Provider instance whose registration is deferred to a subclass.

    Returns
    -------
    None
        Leaves registration to concrete implementations.
    """

class TestApplicationDiscovery(unittest.TestCase):
    """Verify module ownership and provider availability during startup."""

    def testDiscoverProvidersRegistersEachOwnedClassOnce(self) -> None:
        """Register discovered providers in stable order without reexports.

        Returns
        -------
        None
            Assertions validate provider identity and discovery order.
        """
        alpha_name = "test_discovery_alpha_provider"
        beta_name = "test_discovery_beta_provider"
        alpha = type(
            "AlphaProvider",
            (ServiceProvider,),
            {"__module__": alpha_name},
        )
        beta = type(
            "BetaProvider",
            (ServiceProvider,),
            {"__module__": beta_name},
        )
        abstract = type(
            "AbstractProvider",
            (ServiceProvider,),
            {
                "__module__": alpha_name,
                "register": abstractmethod(abstract_registration),
            },
        )
        alpha_module = ModuleType(alpha_name)
        beta_module = ModuleType(beta_name)
        alpha_module.AlphaProvider = alpha
        alpha_module.AbstractProvider = abstract
        alpha_module.BetaAlias = beta
        beta_module.BetaProvider = beta
        app = make_application()
        seen: list[type[ServiceProvider]] = []
        app._Application__storeProviderClass = seen.append

        with patch.dict(
            sys.modules,
            {alpha_name: alpha_module, beta_name: beta_module},
        ):
            app._Application__discoverProviders({beta_name, alpha_name})

        self.assertEqual(seen, [alpha, beta])

    def testLoadPublishesDeferredProvidersBeforeEagerRegistration(self) -> None:
        """Expose deferred service metadata during eager provider registration.

        Returns
        -------
        None
            Assertions validate registration phase access to deferred services.
        """
        app = make_application()
        deferred = {"service": {"module": "provider", "class": "Provider"}}
        app._Application__bootstrap = {"providers": {"deferred": deferred}}
        app._Application__is_compiled = True
        observed: list[object] = []

        def resolve_eager_provider() -> None:
            """Capture deferred metadata during eager registration.

            Returns
            -------
            None
                Appends the visible provider registry.
            """
            observed.append(app._deferred_providers)

        app._Application__resolveEagerProvider = resolve_eager_provider
        app._Application__load()
        self.assertEqual(observed, [deferred])

    def testLoadedConfigurationSeparatesCallerOwnedContainers(self) -> None:
        """Keep committed configuration independent of caller mutations.

        Returns
        -------
        None
            Assertions validate isolation after configuration loading.
        """
        app = make_application()
        overrides = {"app": {"settings": {"items": [1]}}}
        app._Application__bootstrap = {
            "paths": {"config": Path("absent_config_directory")},
            "config": overrides,
        }
        app._Application__loadConfig()
        app._Application__commitConfig()
        overrides["app"]["settings"]["items"].append(2)

        self.assertEqual(app.config("app.settings.items"), [1])

if __name__ == "__main__":
    unittest.main()
