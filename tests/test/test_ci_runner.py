# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING
from unittest import skipUnless
from unittest.mock import patch
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator
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
        """
        Initialize process outcomes and the invocation log.

        Returns
        -------
        None
            Prepare independent exit statuses and subprocess call records.
        """
        self.calls = []
        self.statuses = []
        self.error = None

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
    ) -> subprocess.CompletedProcess[bytes]:
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
        """
        Prepare an isolated runner and a temporary repository fixture.

        Returns
        -------
        None
            Prepare an isolated runner, repository fixture, and output buffers.
        """
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
                self.repo,
                suites,
                continue_on_error=continue_on_error,
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
        """
        Discover all test groups once in deterministic order.

        Returns
        -------
        None
            Assert complete and deterministic test-group discovery.
        """
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
        """
        Return an empty inventory when no matching test files exist.

        Returns
        -------
        None
            Assert an empty suite inventory for an empty repository.
        """
        self.assertEqual(self.runner.discover_suites(self.repo), [])

    def testDiscoveryExcludesOnlyTheLocalRealDatabaseDirectory(self) -> None:
        """
        Exclude local tests while preserving similarly named public paths.

        Returns
        -------
        None
            Assert exclusion of only the local real-database test directory.
        """
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
        """
        Keep an exclusively local test tree out of automatic execution.

        Returns
        -------
        None
            Assert no automatic suites for an exclusively local test tree.
        """
        self._createFile("tests/real_database/test_local.py")
        self._createFile("tests/real_database/mysql/test_connection.py")
        self.assertEqual(self.runner.discover_suites(self.repo), [])

    def testDiscoveryPrunesLocalDatabaseDirectoryBeforeTraversal(self) -> None:
        """Avoid reading excluded directories during suite discovery."""
        self._createFile("tests/alpha/test_public.py")
        excluded = self.repo / "tests" / "real_database"
        excluded.mkdir()
        scandir = os.scandir

        def guarded_scandir(
            path: str | os.PathLike[str],
        ) -> Iterator[os.DirEntry[str]]:
            """Reject traversal into the excluded fixture directory.

            Parameters
            ----------
            path : str | os.PathLike[str]
                Directory requested by the suite walker.

            Returns
            -------
            Iterator[os.DirEntry[str]]
                Directory entries outside the excluded fixture.
            """
            self.assertNotEqual(Path(path), excluded)
            return scandir(path)

        with patch("os.scandir", side_effect=guarded_scandir):
            suites = self.runner.discover_suites(self.repo)
        self.assertEqual([suite.directory for suite in suites], ["tests/alpha"])

    def testDiscoveryPropagatesUnreadableSuiteErrors(self) -> None:
        """Reject incomplete discovery when an allowed suite cannot be read."""
        self._createFile("tests/alpha/test_public.py")
        blocked = self.repo / "tests" / "alpha"
        scandir = os.scandir

        def guarded_scandir(
            path: str | os.PathLike[str],
        ) -> Iterator[os.DirEntry[str]]:
            """Simulate a filesystem failure in an allowed suite.

            Parameters
            ----------
            path : str | os.PathLike[str]
                Directory requested by the suite walker.

            Returns
            -------
            Iterator[os.DirEntry[str]]
                Directory entries when access is allowed.

            Raises
            ------
            PermissionError
                If the requested directory is blocked by the fixture.
            """
            if Path(path) == blocked:
                message = "controlled traversal failure"
                raise PermissionError(message)
            return scandir(path)

        with (
            patch("os.scandir", side_effect=guarded_scandir),
            self.assertRaises(PermissionError),
        ):
            self.runner.discover_suites(self.repo)

    def testFailureStopsBeforeStartingTheNextSuite(self) -> None:
        """
        Preserve the failing exit code and stop subsequent processes.

        Returns
        -------
        None
            Assert early termination with the failing suite's exit code.
        """
        self.processes.statuses = [7, 0, 0]
        self.assertEqual(self._runSuites(), 7)
        self.assertEqual(len(self.processes.calls), 1)
        self.assertIn("FAILED: tests/alpha (exit 7)", self.errors.getvalue())

    def testContinueOnErrorRetainsTheFirstFailure(self) -> None:
        """
        Run remaining suites without losing an earlier failure code.

        Returns
        -------
        None
            Assert continued execution without losing the first failure status.
        """
        self.processes.statuses = [7, 0, 3]
        self.assertEqual(self._runSuites(continue_on_error=True), 7)
        self.assertEqual(len(self.processes.calls), 3)
        for command, _, _, _ in self.processes.calls:
            self.assertIn("--fail-fast=0", command)

    def testTemporaryDirectoryIsInheritedWithoutChangingTheCaller(self) -> None:
        """Pass the chosen temporary path to every child without global changes."""
        temporary = self.repo / "Temporary files ñ"
        with (
            patch.dict(os.environ, {
                "TMPDIR": "caller-tmpdir",
                "TEMP": "caller-temp",
                "TMP": "caller-tmp",
            }),
            contextlib.redirect_stdout(self.output),
        ):
            self.assertEqual(
                self.runner.run_suites(
                    self.repo,
                    [self.runner.TestSuite("tests/alpha")],
                    temporary_directory=temporary,
                ),
                0,
            )
            self.assertEqual(os.environ["TEMP"], "caller-temp")
            self.assertEqual(os.environ["TMP"], "caller-tmp")
            self.assertEqual(os.environ["TMPDIR"], "caller-tmpdir")
        _, _, environment, _ = self.processes.calls[0]
        self.assertEqual(environment["TEMP"], str(temporary))
        self.assertEqual(environment["TMP"], str(temporary))
        self.assertEqual(environment["TMPDIR"], str(temporary))

    @skipUnless(sys.platform == "win32", "Requires Windows path aliases")
    def testWindowsTemporaryProfileUsesAnAliasWithSpacesAndUnicode(self) -> None:
        """Exercise the real Windows alias and clean the owned tree afterward."""
        with (
            contextlib.redirect_stdout(self.output),
            self.runner._windows_temp_directory(enabled=True) as temporary,
        ):
            canonical = temporary.resolve()
            root = canonical.parents[1]
            self.assertNotEqual(temporary, canonical)
            self.assertIn(" ", temporary.name)
            self.assertIn("ñ", temporary.name)
            probe = temporary / "probe.txt"
            probe.write_text("payload", encoding="utf-8")
            self.assertTrue(probe.samefile(canonical / "probe.txt"))
        self.assertFalse(root.exists())

    @skipUnless(sys.platform == "win32", "Requires Windows directory junctions")
    def testWindowsTemporaryProfileFallsBackWhenShortNamesAreDisabled(self) -> None:
        """Keep alias coverage on Windows volumes without 8.3 names."""
        with (
            patch.object(self.runner, "_short_path", side_effect=Path),
            contextlib.redirect_stdout(self.output),
            self.runner._windows_temp_directory(enabled=True) as temporary,
        ):
            root = temporary.resolve().parents[1]
            self.assertTrue(temporary.parent.is_junction())
            self.assertNotEqual(temporary, temporary.resolve())
            (temporary / "probe.txt").write_text("payload", encoding="utf-8")
        self.assertFalse(root.exists())

    @skipUnless(sys.platform == "win32", "Requires Windows directory junctions")
    def testWindowsTemporaryProfileCleansJunctionAfterFailure(self) -> None:
        """Clean the alias and its target after a test-process startup error."""
        failure = OSError("controlled subprocess startup failure")
        with (
            patch.object(self.runner, "_short_path", side_effect=Path),
            contextlib.redirect_stdout(self.output),
            self.assertRaises(OSError) as caught,
            self.runner._windows_temp_directory(enabled=True) as temporary,
        ):
            root = temporary.resolve().parents[1]
            raise failure
        self.assertIs(caught.exception, failure)
        self.assertFalse(root.exists())

    def testWindowsTemporaryProfileIsInactiveOnOtherPlatforms(self) -> None:
        """Avoid Windows API calls on non-Windows test workers."""
        with (
            patch.object(self.runner.sys, "platform", "linux"),
            patch.object(self.runner, "_short_path") as short_path,
            self.runner._windows_temp_directory(enabled=True) as temporary,
        ):
            self.assertIsNone(temporary)
        short_path.assert_not_called()

    def testSuccessfulSuitesUseTheActivePythonAndRepository(self) -> None:
        """
        Pass default verbosity, active Python, repository and UTF-8 settings.

        Returns
        -------
        None
            Assert use of the active interpreter, repository, and UTF-8 settings.
        """
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
        """
        Convert a process signal into a nonzero portable exit status.

        Returns
        -------
        None
            Assert a portable nonzero status for signal termination.
        """
        self.processes.statuses = [-9]
        self.assertEqual(self._runSuites(), 1)

    def testListIncludesQueuesRealtimeAndRootWithoutExecution(self) -> None:
        """
        List the repository inventory without launching child processes.

        Returns
        -------
        None
            Assert inventory listing without starting test subprocesses.
        """
        self.assertEqual(self._main(["--list"]), 0)
        output = self.output.getvalue()
        self.assertIn("tests/queues", output)
        self.assertIn("tests/realtime", output)
        self.assertIn("Root [tests/test_example.py]", output)
        self.assertNotIn("tests/real_database", output)
        self.assertEqual(self.processes.calls, [])

    def testCliUsesDetailedOutputByDefault(self) -> None:
        """
        Pass verbosity two to every suite when the CLI option is omitted.

        Returns
        -------
        None
            Assert detailed CLI output when verbosity is not specified.
        """
        self.assertEqual(self._main([]), 0)
        self.assertTrue(self.processes.calls)
        for command, _, _, _ in self.processes.calls:
            self.assertIn("--verbosity=2", command)
            self.assertNotIn("--start-dir=tests/real_database", command)

    def testCliAppliesContinueAndVerbosityToAllDiscoveredSuites(self) -> None:
        """
        Forward CLI settings while returning an earlier module failure.

        Returns
        -------
        None
            Assert forwarding of CLI options and preservation of prior failure.
        """
        self.processes.statuses = [7]
        self.assertEqual(
            self._main(["--continue-on-error", "--verbosity=0"]),
            7,
        )
        repo = Path(self.runner.__file__).resolve().parents[2]
        self.assertEqual(
            len(self.processes.calls),
            len(self.runner.discover_suites(repo)),
        )
        for command, cwd, _, _ in self.processes.calls:
            self.assertIn("--verbosity=0", command)
            self.assertIn("--fail-fast=0", command)
            self.assertNotIn("--start-dir=tests/real_database", command)
            self.assertEqual(cwd, repo)
        root_commands = [
            command
            for command, _, _, _ in self.processes.calls
            if "--file-pattern=test_example.py" in command
        ]
        self.assertEqual(len(root_commands), 1)
        self.assertIn("--start-dir=tests/test_example.py", root_commands[0])

    def testCliPassesTheWindowsTemporaryProfileToEverySuite(self) -> None:
        """Retain the selected profile through every isolated test process."""
        temporary = self.repo / "Temporary files ñ"
        with patch.object(
            self.runner,
            "_windows_temp_directory",
            return_value=contextlib.nullcontext(temporary),
        ) as profile:
            self.assertEqual(self._main(["--windows-temp"]), 0)
        profile.assert_called_once_with(enabled=True)
        self.assertTrue(self.processes.calls)
        for _, _, environment, _ in self.processes.calls:
            self.assertEqual(environment["TEMP"], str(temporary))
            self.assertEqual(environment["TMP"], str(temporary))
            self.assertEqual(environment["TMPDIR"], str(temporary))

    def testCliReportsTemporaryProfileSetupErrors(self) -> None:
        """Keep temporary-profile failures visible instead of skipping tests."""
        with patch.object(
            self.runner,
            "_windows_temp_directory",
            side_effect=PermissionError("temporary profile denied"),
        ):
            self.assertEqual(self._main(["--windows-temp"]), 2)
        self.assertEqual(self.processes.calls, [])
        self.assertIn("temporary profile denied", self.errors.getvalue())

    def testCliReportsProcessStartupFailure(self) -> None:
        """
        Return a failing status when a child process cannot start.

        Returns
        -------
        None
            Assert a failing CLI status for subprocess startup errors.
        """
        self.processes.error = OSError("process startup failed")
        self.assertEqual(self._main([]), 2)
        self.assertIn("Unable to start test suite", self.errors.getvalue())
