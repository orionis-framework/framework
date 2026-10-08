import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING
from orionis.test import TestCase

if TYPE_CHECKING:
    from types import ModuleType

def _load_runner() -> ModuleType:
    """Load an isolated copy of the shared CI runner.

    Returns
    -------
    ModuleType
        Runner module with independent attributes for each test.
    """
    path = Path(__file__).resolve().parents[2] / ".github/scripts/run_tests.py"
    spec = importlib.util.spec_from_file_location("_orionis_ci_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class _RecordingProcesses:
    """Record process arguments and emit predefined exit statuses."""

    __slots__ = ("calls", "error", "statuses")

    def __init__(self) -> None:
        """Initialize process outcomes and the invocation log."""
        self.calls = []
        self.statuses = []
        self.error = None

    def run(self, command, *, cwd, env, check):
        """Record a subprocess call without launching another interpreter.

        Parameters
        ----------
        command : list[str]
            Program and its individual arguments.
        cwd : Path
            Working directory supplied by the runner.
        env : dict[str, str]
            Environment passed to the child process.
        check : bool
            Whether the process wrapper should raise on a failing status.

        Returns
        -------
        subprocess.CompletedProcess
            Next configured status, or zero when none remain.
        """
        self.calls.append((command, cwd, env, check))
        if self.error is not None:
            raise self.error
        status = self.statuses.pop(0) if self.statuses else 0
        return subprocess.CompletedProcess(command, status)

class TestSharedCiRunner(TestCase):
    """Validate suite discovery and publication gate exit statuses."""

    def setUp(self) -> None:
        """Prepare an isolated runner and a temporary repository fixture."""
        self.runner = _load_runner()
        self.processes = _RecordingProcesses()
        self.runner.subprocess = self.processes
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.output = io.StringIO()
        self.errors = io.StringIO()

    def _createFile(self, path: str) -> None:
        """Create an empty file below the temporary repository.

        Parameters
        ----------
        path : str
            Relative fixture file path.
        """
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")

    def _runSuites(self, *, continue_on_error: bool = False) -> int:
        """Run three module suites with recorded subprocess outcomes.

        Parameters
        ----------
        continue_on_error : bool, optional
            Whether subsequent modules run after a failing module.

        Returns
        -------
        int
            Exit status returned by the runner.
        """
        suites = [
            self.runner.TestSuite(f"tests/{name}")
            for name in ("alpha", "beta", "gamma")
        ]
        with (
            contextlib.redirect_stdout(self.output),
            contextlib.redirect_stderr(self.errors),
        ):
            return self.runner.run_suites(
                self.repo, suites, continue_on_error=continue_on_error,
            )

    def _main(self, arguments: list[str]) -> int:
        """Invoke the CLI while recording its console output.

        Parameters
        ----------
        arguments : list[str]
            CLI options to parse.

        Returns
        -------
        int
            CLI exit status.
        """
        with (
            contextlib.redirect_stdout(self.output),
            contextlib.redirect_stderr(self.errors),
        ):
            return self.runner.main(arguments)

    def testDiscoveryIncludesNestedModulesAndEveryRootFile(self) -> None:
        """Discover all test groups once in deterministic order."""
        for path in (
            "tests/zeta/nested/test_nested.py",
            "tests/alpha/test_first.py",
            "tests/alpha/nested/test_second.py",
            "tests/test_zeta.py",
            "tests/test_alpha.py",
            "tests/helpers/fixture.py",
        ):
            self._createFile(path)
        (self.repo / "tests/test_directory.py").mkdir()
        suites = self.runner.discover_suites(self.repo)
        self.assertEqual(
            [(suite.directory, suite.pattern) for suite in suites],
            [
                ("tests/alpha", "test_*.py"),
                ("tests/zeta", "test_*.py"),
                ("tests", "test_alpha.py"),
                ("tests", "test_zeta.py"),
            ],
        )

    def testDiscoveryReturnsNoSuitesForAnEmptyRepository(self) -> None:
        """Return an empty inventory when no matching test files exist."""
        self.assertEqual(self.runner.discover_suites(self.repo), [])

    def testDiscoveryExcludesOnlyTheLocalRealDatabaseDirectory(self) -> None:
        """Exclude local tests while preserving similarly named public paths."""
        for path in (
            "tests/real_database/test_local.py",
            "tests/real_database/pgsql/nested/test_connection.py",
            "tests/database/real_database/test_public.py",
            "tests/real_database_unit/test_public.py",
            "tests/test_real_database.py",
        ):
            self._createFile(path)
        suites = self.runner.discover_suites(self.repo)
        self.assertEqual(
            [(suite.directory, suite.pattern) for suite in suites],
            [
                ("tests/database", "test_*.py"),
                ("tests/real_database_unit", "test_*.py"),
                ("tests", "test_real_database.py"),
            ],
        )

    def testDiscoveryReturnsNoSuitesForOnlyLocalRealDatabaseTests(self) -> None:
        """Keep an exclusively local test tree out of automatic execution."""
        self._createFile("tests/real_database/test_local.py")
        self._createFile("tests/real_database/mysql/test_connection.py")
        self.assertEqual(self.runner.discover_suites(self.repo), [])

    def testFailureStopsBeforeStartingTheNextSuite(self) -> None:
        """Preserve the failing exit code and stop subsequent processes."""
        self.processes.statuses = [7, 0, 0]
        self.assertEqual(self._runSuites(), 7)
        self.assertEqual(len(self.processes.calls), 1)
        self.assertIn("FAILED: tests/alpha (exit 7)", self.errors.getvalue())

    def testContinueOnErrorRetainsTheFirstFailure(self) -> None:
        """Run remaining suites without losing an earlier failure code."""
        self.processes.statuses = [7, 0, 3]
        self.assertEqual(self._runSuites(continue_on_error=True), 7)
        self.assertEqual(len(self.processes.calls), 3)

    def testSuccessfulSuitesUseTheActivePythonAndRepository(self) -> None:
        """Pass default verbosity, active Python, repository and UTF-8 settings."""
        self.assertEqual(self._runSuites(), 0)
        self.assertEqual(len(self.processes.calls), 3)
        command, cwd, environment, check = self.processes.calls[0]
        self.assertEqual(command[:4], [sys.executable, "-B", "reactor", "test"])
        self.assertIn("--verbosity=1", command)
        self.assertIn("--fail-fast=1", command)
        self.assertEqual(cwd, self.repo)
        self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")
        self.assertFalse(check)

    def testSignalTerminationProducesAFailingPortableStatus(self) -> None:
        """Convert a process signal into a nonzero portable exit status."""
        self.processes.statuses = [-9]
        self.assertEqual(self._runSuites(), 1)

    def testListIncludesQueuesRealtimeAndRootWithoutExecution(self) -> None:
        """List the repository inventory without launching child processes."""
        self.assertEqual(self._main(["--list"]), 0)
        output = self.output.getvalue()
        self.assertIn("tests/queues", output)
        self.assertIn("tests/realtime", output)
        self.assertIn("Root [tests/test_example.py]", output)
        self.assertNotIn("tests/real_database", output)
        self.assertEqual(self.processes.calls, [])

    def testCliUsesDetailedOutputByDefault(self) -> None:
        """Pass verbosity two to every suite when the CLI option is omitted."""
        self.assertEqual(self._main([]), 0)
        self.assertTrue(self.processes.calls)
        for command, _, _, _ in self.processes.calls:
            self.assertIn("--verbosity=2", command)
            self.assertNotIn("--start-dir=tests/real_database", command)

    def testCliAppliesContinueAndVerbosityToAllDiscoveredSuites(self) -> None:
        """Forward CLI settings while returning an earlier module failure."""
        self.processes.statuses = [7]
        self.assertEqual(
            self._main(["--continue-on-error", "--verbosity=0"]), 7,
        )
        repo = Path(self.runner.__file__).resolve().parents[2]
        self.assertEqual(
            len(self.processes.calls), len(self.runner.discover_suites(repo)),
        )
        for command, cwd, _, _ in self.processes.calls:
            self.assertIn("--verbosity=0", command)
            self.assertNotIn("--start-dir=tests/real_database", command)
            self.assertEqual(cwd, repo)
        root_commands = [
            command for command, _, _, _ in self.processes.calls
            if "--file-pattern=test_example.py" in command
        ]
        self.assertEqual(len(root_commands), 1)
        self.assertIn("--start-dir=tests", root_commands[0])

    def testCliReportsProcessStartupFailure(self) -> None:
        """Return a failing status when a child process cannot start."""
        self.processes.error = OSError("process startup failed")
        self.assertEqual(self._main([]), 2)
        self.assertIn("Unable to start test suite", self.errors.getvalue())
