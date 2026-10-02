from __future__ import annotations
import tempfile
from pathlib import Path
import orionis.foundation.application as application_module
from orionis.cache.file_based_cache import FileBasedCache
from orionis.container.context.scope import ScopedContext
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.application import Application
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.support.structures.freezer import FreezeThaw
from orionis.test import TestCase

def make_application(config: dict[str, object] | None = None) -> Application:
    """
    Create an isolated application without replacing the process singleton.

    Parameters
    ----------
    config : dict[str, object] or None, optional
        Configuration to commit before returning the application.

    Returns
    -------
    Application
        Independent application with initialized container state.
    """
    app = object.__new__(Application)
    Application.__init__(app)
    if config is not None:
        app._Application__bootstrap = {"config": config}
        app._Application__commitConfig()
    return app

class FirstProvider(ServiceProvider):
    """Identify the first provider in registration-order assertions."""

class SecondProvider(ServiceProvider):
    """Identify the second provider in registration-order assertions."""

class TestApplicationConfiguration(TestCase):
    """Exercise mutable configuration access and immutable bootstrap snapshots."""

    def setUp(self) -> None:
        """
        Detach the test runner's container scope before application registration.

        Returns
        -------
        None
            Application registrations target their own container state.
        """
        self._scope_token = ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """
        Restore the container scope captured before each test.

        Returns
        -------
        None
            The test runner regains its original container context.
        """
        ScopedContext.reset(self._scope_token)

    def testReadsNestedAndFalsyValues(self) -> None:
        """
        Preserve scalar values and return None for absent or unreachable keys.

        Returns
        -------
        None
            Assertions validate nested lookup behavior.
        """
        values = {"false": False, "zero": 0, "empty": "", "null": None}
        app = make_application({"values": values})
        for key, expected in values.items():
            with self.subTest(key=key):
                self.assertEqual(app.config(f"values.{key}"), expected)
        self.assertIsNone(app.config("missing"))
        self.assertIsNone(app.config("values.false.child"))

    def testRepeatedReadsObserveMutationsThroughReturnedMappings(self) -> None:
        """
        Keep cached paths independent of configuration values and object identity.

        Returns
        -------
        None
            Assertions validate externally visible runtime mutations.
        """
        app = make_application({"app": {"debug": False}})
        self.assertFalse(app.config("app.debug"))
        app.config("app")["debug"] = True
        self.assertTrue(app.config("app.debug"))
        app.config()["app"] = {"debug": "replacement"}
        self.assertEqual(app.config("app.debug"), "replacement")
        app.config("app.debug", False)
        self.assertFalse(app.config("app.debug"))

    def testWritesReplaceScalarParentsAndPreserveEmptyKeySegments(self) -> None:
        """
        Create missing mappings while preserving the dot-notation contract.

        Returns
        -------
        None
            Assertions validate nested writes and empty keys.
        """
        app = make_application({"root": False})
        self.assertEqual(app.config("root.child.value", 7), 7)
        self.assertEqual(app.config("root.child.value"), 7)
        app.config("", "empty")
        self.assertEqual(app.config(""), "empty")
        app.config("root..leaf", None)
        self.assertEqual(app.config("root"), {
            "child": {"value": 7}, "": {"leaf": None},
        })

    def testResetRestoresBootstrapAfterNestedMutations(self) -> None:
        """
        Restore isolated runtime containers without retaining stale cached values.

        Returns
        -------
        None
            Assertions validate mutable runtime and frozen bootstrap isolation.
        """
        app = make_application({"app": {"debug": False, "items": [1, 2]}})
        app.config("app.items").append(3)
        app.config("app.debug", True)
        self.assertTrue(app.resetRuntimeConfig())
        self.assertFalse(app.config("app.debug"))
        self.assertEqual(app.config("app.items"), [1, 2])

    def testManyDistinctKeysKeepReadsAndWritesCorrect(self) -> None:
        """
        Bound retained lookup paths while supporting arbitrary configuration keys.

        Returns
        -------
        None
            Assertions validate cache bounds and accesses after cache turnover.
        """
        app = make_application({})
        for index in range(600):
            self.assertEqual(app.config(f"dynamic.item{index}", index), index)
        self.assertLessEqual(
            application_module._parse_config_key.cache_info().currsize, 256,
        )
        for index in range(600):
            self.assertEqual(app.config(f"dynamic.item{index}"), index)
        self.assertLessEqual(
            application_module._parse_config_key.cache_info().currsize, 256,
        )

    def testCacheOverflowPreservesFrequentlyReadPaths(self) -> None:
        """
        Keep frequently used paths cached while unrelated configuration keys vary.

        Returns
        -------
        None
            Assertions validate bounded storage and a hit for the frequent key.
        """
        app = make_application({"stable": {"value": 7}})
        for index in range(600):
            self.assertEqual(app.config("stable.value"), 7)
            app.config(f"dynamic.item{index}", index)
        cache_info = application_module._parse_config_key.cache_info
        previous_hits = cache_info().hits
        self.assertEqual(app.config("stable.value"), 7)
        self.assertEqual(cache_info().hits, previous_hits + 1)
        self.assertLessEqual(cache_info().currsize, 256)

    def testAccessRejectsUnconfiguredApplicationsAndInvalidKeys(self) -> None:
        """
        Report initialization and key-type errors before traversing configuration.

        Returns
        -------
        None
            Assertions validate the public error contract.
        """
        app = make_application()
        with self.assertRaises(RuntimeError):
            app.config("app.debug")
        app = make_application({})
        for key in (1, [], {}):
            with self.subTest(key=key), self.assertRaises(TypeError):
                app.config(key)
        with self.assertRaises(TypeError):
            app.config(None, True)

    def testPathOverridesPreserveStringAndPathResolution(self) -> None:
        """
        Resolve defaults and overrides using their existing base-directory rules.

        Returns
        -------
        None
            Assertions validate default paths and supported override forms.
        """
        app = make_application()
        app.withConfigPaths(
            config="custom/config",
            routes=Path("custom/routes"),
            storage=None,
            ignored="ignored/path",
        )
        app._Application__commitConfig()
        self.assertEqual(app.path("root"), app.basePath)
        self.assertEqual(app.path("config"), (app.basePath / "custom/config").resolve())
        self.assertEqual(app.path("routes"), Path("custom/routes").resolve())
        self.assertEqual(app.path("storage"), (app.basePath / "storage").resolve())
        self.assertEqual(set(app.path()), {"root", *CORE_APP_PATHS})

    def testRegisteringAnExistingProviderRestoresItsPriority(self) -> None:
        """
        Keep eager providers unique and move re-registered providers to the front.

        Returns
        -------
        None
            Assertions validate provider ordering and metadata.
        """
        app = make_application()
        app.withProviders(FirstProvider, SecondProvider, FirstProvider)
        eager = app._Application__bootstrap["providers"]["eager"]
        self.assertEqual(list(eager), [
            f"{FirstProvider.__module__}.{FirstProvider.__name__}",
            f"{SecondProvider.__module__}.{SecondProvider.__name__}",
        ])

    def testCompiledSnapshotRoundTripsWithoutMutatingBootstrap(self) -> None:
        """
        Persist a bootstrap snapshot while leaving its mutable containers intact.

        Returns
        -------
        None
            Assertions validate cache serialization and configuration integrity.
        """
        app = make_application()
        app.withConfigApp(debug=False, nested={"items": [1, 2]})
        bootstrap = app._Application__bootstrap
        expected = FreezeThaw.thaw(bootstrap)
        with tempfile.TemporaryDirectory() as directory:
            cache = FileBasedCache(Path(directory), "config")
            app._Application__compiled = True
            app._Application__compiled_state_store = cache
            app._Application__persistCompiledState()
            self.assertIs(app._Application__bootstrap, bootstrap)
            self.assertEqual(bootstrap, expected)
            self.assertEqual(cache.get(), expected)

    def testBootstrapMetadataCopiesRemainIndependent(self) -> None:
        """
        Isolate mutable bootstrap descriptors from other application snapshots.

        Returns
        -------
        None
            Changes to one descriptor never affect the next bootstrap snapshot.
        """
        app = make_application()
        first = app._Application__defaultBootstrap()
        second = app._Application__defaultBootstrap()
        first["kernels"]["KernelHTTP"]["class"] = "CustomKernel"
        first["exception_handler"]["class"] = "CustomHandler"
        first["scheduler"]["class"] = "CustomScheduler"
        self.assertEqual(second["kernels"]["KernelHTTP"]["class"], "KernelHTTP")
        self.assertEqual(second["exception_handler"]["class"], "BaseExceptionHandler")
        self.assertEqual(second["scheduler"]["class"], "BaseScheduler")
        self.assertNotIn("commands", second)

    def testCreateCapturesCallerAndInitializesOnlyOnce(self) -> None:
        """
        Retain entry-point detection and idempotent application creation.

        Returns
        -------
        None
            Assertions validate caller metadata and one bootstrap invocation.
        """
        app = make_application()
        boot_calls = []

        def load_config() -> None:
            """
            Commit a configuration without discovering external application files.

            Returns
            -------
            None
                The isolated application has a readable configuration snapshot.
            """
            boot_calls.append(None)
            app._Application__bootstrap = {
                "config": {"app": {"env": "testing", "debug": False}},
                "paths": {
                    "storage_framework": app.basePath / "storage" / "framework",
                },
                "providers": {},
            }
            app._Application__commitConfig()

        app._Application__load = load_config
        self.assertIsNone(app.entryPoint)
        self.assertIs(app.create(), app)
        self.assertIs(app.create(), app)
        self.assertEqual(len(boot_calls), 1)
        self.assertTrue(app.isBooted)
        self.assertEqual(app._Application__entry_point, __file__)
        self.assertEqual(
            app.entryPoint,
            "tests.foundation.test_application_config:app",
        )

    def testCompileLoadsAndCommitsPreviouslyPersistedConfiguration(self) -> None:
        """
        Reuse a compiled snapshot through the public cache-configuration method.

        Returns
        -------
        None
            Assertions validate cold-cache persistence and warm-cache loading.
        """
        with tempfile.TemporaryDirectory() as directory:
            first = make_application()
            first.compile(path=directory)
            first.withConfigApp(debug=False, settings={"values": [1, 2]})
            first._Application__persistCompiledState()
            second = make_application()
            second.compile(path=directory)
            self.assertTrue(second.compiled)
            self.assertEqual(second.compiledPath, Path(directory).resolve())
            self.assertFalse(second.config("app.debug"))
            self.assertEqual(second.config("app.settings.values"), [1, 2])
            second.withConfigApp(debug=True)
            self.assertFalse(second.config("app.debug"))

    def testRoutingResultsRemainIsolatedMutableLists(self) -> None:
        """
        Return independent lists when exposing frozen routing configuration.

        Returns
        -------
        None
            Assertions validate routing result types and snapshot isolation.
        """
        app = make_application()
        route = Path("routes/api.py")
        app._Application__bootstrap = {
            "routing": {"api": [route], "health": "/health"},
        }
        app._Application__commitConfig()
        app.routingPaths("api").clear()
        app.routingPaths()["api"].append(Path("routes/other.py"))
        self.assertEqual(app.routingPaths("api"), [route])
        self.assertIsNone(app.routingPaths("health"))
