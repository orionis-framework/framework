import json
import shutil
import sys
import tempfile
from pathlib import Path
from orionis.test import TestCase
from orionis.test.cases.case import TestCase as CoreTestCase
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.core.engine import TestingEngine
from orionis.test.entities.result import TestResult
from orionis.test.enums.status import TestStatus
from orionis.test.executors.results import TestResultProcessor

# Package name used for every generated module tree.
_PACKAGE: str = "_orionis_probe_suite"

# Generated module exposing a single passing test method.
_PASSING_SOURCE: str = '''from orionis.test import TestCase

class GeneratedPassingCase(TestCase):

    def testGeneratedPasses(self) -> None:
        """Assert a condition that always holds."""
        self.assertEqual(1, 1)
'''

# Generated module exposing a single failing test method.
_FAILING_SOURCE: str = '''from orionis.test import TestCase

class GeneratedFailingCase(TestCase):

    def testGeneratedFails(self) -> None:
        """Assert a condition that never holds."""
        self.assertEqual(1, 2)
'''

# Generated module exposing two methods with different name prefixes.
_MIXED_SOURCE: str = '''from orionis.test import TestCase

class GeneratedMixedCase(TestCase):

    def testAlphaGenerated(self) -> None:
        """Assert a condition that always holds."""
        self.assertEqual(1, 1)

    def testBetaGenerated(self) -> None:
        """Assert a condition that always holds."""
        self.assertEqual(2, 2)
'''

# Generated module that cannot be imported.
_BROKEN_SOURCE: str = "def broken(:\n"

class _StubApp:
    """Application double exposing only the members read by the engine."""

    __slots__ = ("_config", "_storage", "basePath")

    def __init__(
        self,
        base_path: Path,
        storage: Path,
        config: dict[str, object] | None = None,
    ) -> None:
        self.basePath: Path = base_path
        self._storage: Path = storage
        self._config: dict[str, object] = {
            "testing.verbosity": 0,
            "testing.fail_fast": False,
            "testing.start_dir": str(base_path / _PACKAGE),
            "testing.file_pattern": "test_*.py",
            "testing.method_pattern": "test*",
            "testing.cache_results": False,
        }
        if config:
            self._config.update(config)

    def config(self, key: str) -> object:
        """Return the configured value registered under the given key."""
        return self._config[key]

    def path(self, _key: str) -> Path:
        """Return the storage directory regardless of the requested key."""
        return self._storage

def _engine_state(engine: TestingEngine, name: str) -> object:
    """Read a private engine attribute to verify configuration handling."""
    return getattr(engine, f"_TestingEngine__{name}")

def _write_module(directory: Path, name: str, source: str) -> None:
    """Write a generated module inside the given directory."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.py").write_text(source, encoding="utf-8")

def _count_import_entries(entry: str) -> int:
    """Count how many times a directory is registered for imports."""
    return sys.path.count(entry)

class _EngineTestCase(TestCase):
    """Base scenario creating an isolated project tree for every test."""

    def setUp(self) -> None:
        """
        Create a disposable project tree before each scenario.

        Guarantees that discovery always runs against a controlled set
        of generated modules.
        """
        self._root = Path(tempfile.mkdtemp(prefix="orionis-engine-"))
        self._suite_dir = self._root / _PACKAGE
        self._suite_dir.mkdir(parents=True, exist_ok=True)
        self._storage = self._root / "storage"
        self._sys_path = list(sys.path)
        self._verbosity = TestResultProcessor._print_verbosity

    def tearDown(self) -> None:
        """
        Discard every side effect produced by the scenario.

        Restores the import machinery, the reporting verbosity and
        removes the generated project tree.
        """
        sys.path[:] = self._sys_path
        for name in [n for n in sys.modules if n.startswith(_PACKAGE)]:
            sys.modules.pop(name, None)
        TestResultProcessor._print_verbosity = self._verbosity
        CoreTestCase.setMethodPattern("test*")
        shutil.rmtree(self._root, ignore_errors=True)

    def _makeEngine(self, config: dict[str, object] | None = None) -> TestingEngine:
        """Build an engine bound to a stubbed application."""
        app = _StubApp(self._root, self._storage, config)
        return TestingEngine(app)  # type: ignore[arg-type]

    def _cacheFolder(self) -> Path:
        """Return the folder where cached reports are expected."""
        return self._storage / "framework" / "cache" / "testing"

class TestTestingEngineConfiguration(_EngineTestCase):

    def testEngineSatisfiesTheContract(self) -> None:
        """
        Build an engine that honours the testing contract.

        Validates that the concrete engine can be injected wherever the
        contract is requested.
        """
        self.assertIsInstance(self._makeEngine(), ITestingEngine)

    def testConfigurationValuesAreStored(self) -> None:
        """
        Read every supported option from the application configuration.

        Validates that the engine is fully driven by configuration
        instead of hard coded defaults.
        """
        engine = self._makeEngine({
            "testing.verbosity": 2,
            "testing.file_pattern": "check_*.py",
            "testing.method_pattern": "check*",
        })
        self.assertEqual(_engine_state(engine, "verbosity"), 2)
        self.assertEqual(_engine_state(engine, "file_pattern"), "check_*.py")
        self.assertEqual(_engine_state(engine, "method_pattern"), "check*")

    def testBasePathAndCacheFolderAreResolved(self) -> None:
        """
        Resolve the base path and the report cache folder on creation.

        Validates that cached reports are written under the storage
        directory published by the application.
        """
        engine = self._makeEngine()
        self.assertEqual(_engine_state(engine, "base_path"), self._root)
        self.assertEqual(_engine_state(engine, "cache_folder"), self._cacheFolder())

    def testTruthyFailFastValuesAreAccepted(self) -> None:
        """
        Interpret every supported truthy representation of fail fast.

        Validates that environment driven configuration values are
        normalised into a boolean.
        """
        for value in (1, True, "1", "true", "True"):
            engine = self._makeEngine({"testing.fail_fast": value})
            self.assertIs(_engine_state(engine, "fail_fast"), True)

    def testFalsyFailFastValuesAreRejected(self) -> None:
        """
        Interpret unsupported representations of fail fast as disabled.

        Validates that only the documented truthy values enable the
        early exit behaviour.
        """
        for value in (0, False, "0", "false", "no", None):
            engine = self._makeEngine({"testing.fail_fast": value})
            self.assertIs(_engine_state(engine, "fail_fast"), False)

    def testStartPanelIsEnabledByDefault(self) -> None:
        """
        Enable the start panel unless it is explicitly disabled.

        Validates the default presentation behaviour of a freshly built
        engine.
        """
        self.assertIs(_engine_state(self._makeEngine(), "with_panel"), True)

class TestTestingEngineSetters(_EngineTestCase):

    def testSetVerbosityStoresValueAndReturnsSelf(self) -> None:
        """
        Store the requested verbosity and allow further chaining.

        Validates the fluent contract exposed to the console command.
        """
        engine = self._makeEngine()
        self.assertIs(engine.setVerbosity(2), engine)
        self.assertEqual(_engine_state(engine, "verbosity"), 2)

    def testSetFailFastStoresValueAndReturnsSelf(self) -> None:
        """
        Store the fail fast flag and allow further chaining.

        Validates that the early exit behaviour can be toggled at
        runtime.
        """
        engine = self._makeEngine()
        self.assertIs(engine.setFailFast(fail_fast=True), engine)
        self.assertIs(_engine_state(engine, "fail_fast"), True)

    def testSetStartDirStoresValueAndReturnsSelf(self) -> None:
        """
        Store the discovery root and allow further chaining.

        Validates that the console command can narrow a run to a single
        directory.
        """
        engine = self._makeEngine()
        self.assertIs(engine.setStartDir("tests"), engine)
        self.assertEqual(_engine_state(engine, "start_dir"), "tests")

    def testSetFilePatternStoresValueAndReturnsSelf(self) -> None:
        """
        Store the file pattern and allow further chaining.

        Validates that discovery can be restricted to a subset of the
        generated modules.
        """
        engine = self._makeEngine()
        self.assertIs(engine.setFilePattern("check_*.py"), engine)
        self.assertEqual(_engine_state(engine, "file_pattern"), "check_*.py")

    def testSetMethodPatternStoresValueAndReturnsSelf(self) -> None:
        """
        Store the method pattern and allow further chaining.

        Validates that the engine keeps its own copy of the pattern used
        while filtering discovered cases.
        """
        engine = self._makeEngine()
        self.assertIs(engine.setMethodPattern("check*"), engine)
        self.assertEqual(_engine_state(engine, "method_pattern"), "check*")

    def testSetMethodPatternPropagatesToTheTestCase(self) -> None:
        """
        Propagate the method pattern to the shared test case class.

        Validates that wrapping and discovery always agree on which
        methods are considered tests.
        """
        self._makeEngine().setMethodPattern("check*")
        self.assertIsNotNone(CoreTestCase._method_regex.match("checkSomething"))
        self.assertIsNone(CoreTestCase._method_regex.match("testSomething"))

    def testWithoutPanelDisablesTheStartPanelAndReturnsSelf(self) -> None:
        """
        Disable the start panel and allow further chaining.

        Validates that embedded runs can suppress the decorative output.
        """
        engine = self._makeEngine()
        self.assertIs(engine.withoutPanel(), engine)
        self.assertIs(_engine_state(engine, "with_panel"), False)

    def testSettersCanBeChained(self) -> None:
        """
        Configure the engine through a single fluent expression.

        Validates that every setter returns the engine so calls compose
        naturally.
        """
        engine = self._makeEngine()
        configured = (
            engine
            .setVerbosity(1)
            .setFailFast(fail_fast=True)
            .setStartDir("tests")
            .setFilePattern("test_*.py")
            .setMethodPattern("test*")
            .withoutPanel()
        )
        self.assertIs(configured, engine)

class TestTestingEngineDiscovery(_EngineTestCase):

    def testDiscoverCollectsGeneratedTests(self) -> None:
        """
        Collect every test declared by a generated module.

        Validates the happy path of discovery over a controlled project
        tree.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        self.assertEqual(self._makeEngine().discover().countTestCases(), 1)

    def testDiscoverTraversesDirectoriesWithoutInitFiles(self) -> None:
        """
        Traverse nested folders that are not importable packages.

        Validates the manual directory walk that replaces the standard
        discovery mechanism.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        _write_module(self._suite_dir / "nested", "test_nested", _MIXED_SOURCE)
        self.assertEqual(self._makeEngine().discover().countTestCases(), 3)

    def testDiscoverIgnoresFilesOutsideThePattern(self) -> None:
        """
        Ignore modules whose file name does not match the pattern.

        Validates that helper modules living next to the tests are never
        executed.
        """
        _write_module(self._suite_dir, "helper_passing", _PASSING_SOURCE)
        self.assertEqual(self._makeEngine().discover().countTestCases(), 0)

    def testDiscoverFiltersMethodsByPattern(self) -> None:
        """
        Keep only the methods matching the configured method pattern.

        Validates that a run can be narrowed down to a single method
        family.
        """
        _write_module(self._suite_dir, "test_mixed", _MIXED_SOURCE)
        engine = self._makeEngine({"testing.method_pattern": "testAlpha*"})
        self.assertEqual(engine.discover().countTestCases(), 1)

    def testDiscoverSkipsModulesThatCannotBeImported(self) -> None:
        """
        Skip modules raising an error while being imported.

        Validates that a single broken file never aborts the whole
        discovery phase.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        _write_module(self._suite_dir, "test_broken", _BROKEN_SOURCE)
        self.assertEqual(self._makeEngine().discover().countTestCases(), 1)

    def testDiscoverReturnsEmptySuiteWhenNothingMatches(self) -> None:
        """
        Return an empty suite when the tree contains no test module.

        Validates that discovery degrades gracefully instead of raising.
        """
        self.assertEqual(self._makeEngine().discover().countTestCases(), 0)

    def testDiscoverRegistersTheTopLevelDirectoryOnce(self) -> None:
        """
        Register the project root in the import path exactly once.

        Validates that repeated discovery never grows the interpreter
        search path.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        engine = self._makeEngine()
        engine.discover()
        engine.discover()
        top_level = self._root.absolute().as_posix()
        self.assertEqual(_count_import_entries(top_level), 1)

    def testDiscoverReturnsIndependentSuites(self) -> None:
        """
        Build a fresh suite on every discovery call.

        Validates that results of consecutive discoveries never
        accumulate in a shared container.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        engine = self._makeEngine()
        first = engine.discover()
        second = engine.discover()
        self.assertIsNot(first, second)
        self.assertEqual(first.countTestCases(), second.countTestCases())

class TestTestingEngineExecution(_EngineTestCase):

    async def testRunReturnsResultsForPassingTests(self) -> None:
        """
        Report a passed result for every successful generated test.

        Validates the end to end execution path of the engine.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        results = await self._makeEngine().withoutPanel().run()
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], TestResult)
        self.assertEqual(results[0].status, TestStatus.PASSED)

    async def testRunReportsFailingTests(self) -> None:
        """
        Report a failed result for every unsuccessful generated test.

        Validates that assertion errors are captured instead of
        propagated to the caller.
        """
        _write_module(self._suite_dir, "test_failing", _FAILING_SOURCE)
        results = await self._makeEngine().withoutPanel().run()
        self.assertEqual(results[0].status, TestStatus.FAILED)
        self.assertIsNotNone(results[0].error_message)

    async def testRunReturnsEmptyListWhenNothingIsDiscovered(self) -> None:
        """
        Return an empty report when the tree contains no test.

        Validates that an empty run is a supported outcome rather than
        an error.
        """
        self.assertEqual(await self._makeEngine().withoutPanel().run(), [])

    async def testRepeatedRunsDoNotAccumulateTests(self) -> None:
        """
        Execute the same amount of tests when a run is repeated.

        Validates that every run discovers a fresh suite instead of
        appending to the previously executed one.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        engine = self._makeEngine().withoutPanel()
        first = await engine.run()
        second = await engine.run()
        self.assertEqual(len(second), len(first))

    async def testRunAppliesTheConfiguredVerbosity(self) -> None:
        """
        Publish the configured verbosity to the result processor.

        Validates that the console output detail level is controlled by
        the engine configuration.
        """
        engine = self._makeEngine({"testing.verbosity": 0})
        await engine.withoutPanel().run()
        self.assertEqual(TestResultProcessor._print_verbosity, 0)

    async def testRunWithoutCacheWritesNoReport(self) -> None:
        """
        Skip report persistence when result caching is disabled.

        Validates that the storage directory stays untouched for a
        regular run.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        await self._makeEngine().withoutPanel().run()
        self.assertFalse(self._cacheFolder().exists())

    async def testRunWithCacheWritesJsonReport(self) -> None:
        """
        Persist the report as JSON when result caching is enabled.

        Validates that every executed test is exported with its name and
        status.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        engine = self._makeEngine({"testing.cache_results": True})
        await engine.withoutPanel().run()
        reports = list(self._cacheFolder().glob("*.json"))
        self.assertEqual(len(reports), 1)
        payload = json.loads(reports[0].read_text(encoding="utf-8"))
        self.assertEqual(payload[0]["status"], "PASSED")

    async def testRunWithCacheCreatesTheReportFolder(self) -> None:
        """
        Create the report folder when it does not exist yet.

        Validates that a first cached run does not require any manual
        preparation of the storage tree.
        """
        _write_module(self._suite_dir, "test_passing", _PASSING_SOURCE)
        engine = self._makeEngine({"testing.cache_results": True})
        await engine.withoutPanel().run()
        self.assertTrue(self._cacheFolder().is_dir())
