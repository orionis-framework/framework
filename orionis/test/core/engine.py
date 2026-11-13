# ruff: noqa: TC001
# Keep the application contract available for runtime dependency injection.
"""Discover configured tests, execute them and persist optional result caches."""

import asyncio
import fnmatch
import json
import os
import re
import sys
import time
import unittest
from typing import NoReturn, Self, TYPE_CHECKING
from uuid import uuid4
from orionis.foundation.contracts.application import IApplication
from orionis.test.cases.case import _METHOD_PATTERN
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.executors.runner import TestRunner
from pathlib import Path

if TYPE_CHECKING:
    from collections.abc import Generator
    from orionis.test.entities.result import TestResult
    from orionis.test.executors.results import TestResultProcessor

# Fallbacks mirroring orionis.foundation.config.testing.Testing, applied when a
# configuration key is absent (app.config returns None for unknown keys).
_DEFAULT_VERBOSITY: int = 2
"""
Fallbacks mirroring orionis.foundation.config.testing.Testing, applied when a
configuration key is absent (app.config returns None for unknown keys).
"""
_DEFAULT_START_DIR: str = "tests"
"""Default start dir identifier: ``tests``."""
_DEFAULT_FILE_PATTERN: str = "test_*.py"
"""Default file pattern identifier: ``test_*.py``."""
_DEFAULT_METHOD_PATTERN: str = "test*"
"""Default method pattern identifier: ``test*``."""


def _raise_discovery_error(error: OSError) -> NoReturn:
    """Propagate traversal errors instead of silently omitting test directories.

    Parameters
    ----------
    error : OSError
        Filesystem error reported while walking the discovery tree.

    Returns
    -------
    typing.NoReturn
        No value is returned because the supplied exception is always raised.

    Raises
    ------
    OSError
        Always propagate the original filesystem error.
    """
    raise error


class _PatternTestLoader(unittest.TestLoader):
    """Filter short method names before constructing test case instances."""

    def __init__(self, matcher: re.Pattern[str]) -> None:
        """Store the configured matcher and accept any method prefix.

        Parameters
        ----------
        matcher : re.Pattern[str]
            Compiled shell-style pattern for individual method names.

        Returns
        -------
        None
            No return value.
        """
        super().__init__()
        self.testMethodPrefix = ""
        """Allow the configured matcher to select any method prefix."""
        self.__matcher = matcher
        """Compiled pattern selecting short test method names."""

    def getTestCaseNames(self, test_case_class: type[unittest.TestCase]) -> list[str]:
        """Return callable methods matching the configured short-name pattern.

        Parameters
        ----------
        test_case_class : type[unittest.TestCase]
            Class whose test method names are selected.

        Returns
        -------
        list[str]
            Matching names in the native loader's configured order.
        """
        return [
            name
            for name in super().getTestCaseNames(test_case_class)
            if self.__matcher.match(name) is not None
        ]


class TestingEngine(ITestingEngine):
    """Discover configured tests, execute them and persist optional result caches."""

    def __init__(
        self,
        app: IApplication,
    ) -> None:
        """
        Initialize the TestingEngine with application configuration.

        Every ``testing.*`` key that is absent from the application
        configuration resolves to None and is replaced by the default declared
        in ``orionis.foundation.config.testing.Testing``, so discovery never
        receives a missing value.

        Parameters
        ----------
        app : orionis.IApplication
            Application instance providing configuration values.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Verbosity needs an explicit check because 0 is a valid level.
        verbosity = app.config("testing.verbosity")

        # Retrieve configuration values from the application instance.
        self.__base_path: Path = app.basePath
        """Retrieve configuration values from the application instance."""
        self.__verbosity: int = _DEFAULT_VERBOSITY if verbosity is None else verbosity
        """Configured detail level for test-runner output."""
        self.__fail_fast: bool = app.config("testing.fail_fast") in [
            1,
            True,
            "1",
            "true",
            "True",
        ]
        """Whether the test run stops after the first failure."""
        self.__start_dir: str = app.config("testing.start_dir") or _DEFAULT_START_DIR
        """Directory from which test discovery begins."""
        self.__file_pattern: str = (
            app.config("testing.file_pattern") or _DEFAULT_FILE_PATTERN
        )
        """Filename pattern selecting modules for test discovery."""
        self.__method_pattern: str = (
            app.config("testing.method_pattern") or _DEFAULT_METHOD_PATTERN
        )
        """Method-name pattern selecting test cases."""
        self.__json_cache: bool = bool(app.config("testing.cache_results"))
        """Json cache produced by ``bool``."""
        self.__cache_folder: Path = app.path("storage_framework") / "cache" / "testing"
        """Directory used to persist structured test-run results."""
        self.__with_panel: bool = True  # Default to showing the start panel
        """With panel flag used by ``TestingEngine``."""

    def setVerbosity(self, verbosity: int) -> Self:
        """
        Set the verbosity level for the testing engine.

        Parameters
        ----------
        verbosity : int
            Verbosity level to set.

        Returns
        -------
        typing.Self
            Returns self for method chaining.
        """
        self.__verbosity = verbosity
        return self

    def setFailFast(self, *, fail_fast: bool) -> Self:
        """
        Set the fail-fast behavior for the testing engine.

        Parameters
        ----------
        fail_fast : bool
            Whether to stop on first failure.

        Returns
        -------
        typing.Self
            Returns self for method chaining.
        """
        self.__fail_fast = fail_fast
        return self

    def setStartDir(self, start_dir: str) -> Self:
        """
        Set the directory or Python file used for test discovery.

        Parameters
        ----------
        start_dir : str
            Directory or Python file, relative to the application root when
            not absolute.

        Returns
        -------
        typing.Self
            Returns self for method chaining.
        """
        self.__start_dir = start_dir
        return self

    def setFilePattern(self, file_pattern: str) -> Self:
        """
        Set the file pattern for test file discovery.

        Parameters
        ----------
        file_pattern : str
            Pattern to match test files.

        Returns
        -------
        typing.Self
            Returns self for method chaining.
        """
        self.__file_pattern = file_pattern
        return self

    def setMethodPattern(self, method_pattern: str) -> Self:
        """
        Set the method pattern for test method discovery.

        Parameters
        ----------
        method_pattern : str
            Pattern to match test methods.

        Returns
        -------
        typing.Self
            Returns self for method chaining.
        """
        # Apply this pattern only while discovering this engine's own cases.
        self.__method_pattern = method_pattern
        return self

    def withoutPanel(self) -> Self:
        """
        Disable the start panel display for the testing engine.

        Returns
        -------
        typing.Self
            Returns self for method chaining.
        """
        self.__with_panel = False
        return self

    def __extractTests(
        self,
        test_suite: unittest.TestSuite,
    ) -> Generator[unittest.TestCase]:
        """
        Extract individual test cases from a test suite recursively.

        Parameters
        ----------
        test_suite : unittest.TestSuite
            Test suite to extract test cases from.

        Yields
        ------
        unittest.TestCase
            Individual test case contained in the suite.
        """
        # Recursively extract test cases from nested suites.
        for test in test_suite:
            if isinstance(test, unittest.TestSuite):
                yield from self.__extractTests(test)
            else:
                yield test

    def __testFiles(self, start_path: Path) -> Generator[Path]:
        """Yield matching Python files without traversing an explicit file path.

        Parameters
        ----------
        start_path : pathlib.Path
            Existing directory or Python file selected for discovery.

        Yields
        ------
        pathlib.Path
            File to import as a test module.

        Raises
        ------
        ValueError
            If an explicitly selected file does not have a Python extension.
        OSError
            If the discovery tree cannot be read.
        """
        if start_path.is_file():
            if start_path.suffix != ".py":
                message = "Test discovery requires a directory or Python file."
                raise ValueError(message)
            yield start_path
            return

        for directory, directories, filenames in os.walk(
            start_path,
            onerror=_raise_discovery_error,
        ):
            directories.sort()
            for filename in sorted(filenames):
                if fnmatch.fnmatch(filename, self.__file_pattern):
                    yield Path(directory) / filename

    def discover(self) -> unittest.TestSuite:
        """
        Discover and filter tests using configuration parameters.

        Returns
        -------
        unittest.TestSuite
            Test suite containing filtered test cases.

        Raises
        ------
        OSError
            If the selected path is absent or a directory cannot be read.
        ValueError
            If the selected path is outside the application or is not Python.
        ImportError
            If a matching module was imported from another project directory.
        Exception
            If a test module raises an exception outside loader error handling.
        """
        # Resolve the project root before deriving module names from test paths.
        base_path = self.__base_path.resolve()
        top_level_dir: str = base_path.as_posix()
        if top_level_dir not in sys.path:
            sys.path.insert(0, top_level_dir)

        start_path = (base_path / self.__start_dir).resolve(strict=True)
        start_path.relative_to(base_path)

        # Use a fresh TestLoader to avoid shared state in defaultTestLoader.
        matcher = re.compile(fnmatch.translate(self.__method_pattern))
        loader = _PatternTestLoader(matcher)
        filtered_suite: unittest.TestSuite = unittest.TestSuite()

        # Construct cases with this engine's matcher and restore the caller's
        # context even if loading a module fails.
        token = _METHOD_PATTERN.set(matcher)
        try:
            for filepath in self.__testFiles(start_path):
                relative = filepath.with_suffix("").relative_to(base_path)
                module_name = ".".join(relative.parts)
                errors_before = len(loader.errors)
                tests = loader.loadTestsFromName(module_name)
                # Preserve loader failures regardless of the method filter.
                if len(loader.errors) != errors_before:
                    filtered_suite.addTests(tests)
                    continue
                module_file = getattr(sys.modules.get(module_name), "__file__", None)
                if (
                    module_file is None
                    or Path(module_file).resolve() != filepath.resolve()
                ):
                    message = (
                        f"Test module {module_name!r} was imported from "
                        f"{module_file!r}, but discovery selected {str(filepath)!r}."
                    )
                    raise ImportError(message)
                for test_case in self.__extractTests(tests):
                    method_name = getattr(test_case, "_testMethodName", None)
                    if method_name and fnmatch.fnmatch(
                        method_name,
                        self.__method_pattern,
                    ):
                        filtered_suite.addTest(test_case)
        finally:
            _METHOD_PATTERN.reset(token)

        return filtered_suite

    def __saveCache(self, results: list[TestResult]) -> None:
        """
        Save test results to an independent JSON cache file.

        Parameters
        ----------
        results : list[orionis.test.entities.result.TestResult]
            List of test results to save.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Ensure the cache folder exists
        self.__cache_folder.mkdir(parents=True, exist_ok=True)

        data = [result.toDict() for result in results]
        timestamp = int(time.time())
        full_path = self.__cache_folder / f"{timestamp}-{uuid4().hex}.json"
        with full_path.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=4, default=str)

    async def run(self) -> list[TestResult]:
        """
        Run the discovered test suite asynchronously.

        Discovers the tests, builds a runner carrying the configured verbosity,
        and executes them using a thread pool to avoid blocking. Saves results
        to cache if enabled.

        Returns
        -------
        list[orionis.test.entities.result.TestResult]
            List of TestResult objects containing test execution outcomes.
        """
        # Build a fresh suite so consecutive runs never accumulate tests.
        suite: unittest.TestSuite = self.discover()

        # Create runner with current configuration. The verbosity travels with
        # the runner instance and reaches the result processor it builds.
        runner = TestRunner(
            verbosity=self.__verbosity,
            failfast=self.__fail_fast,
            with_panel=self.__with_panel,
        )

        # Offload the synchronous runner to a thread pool to avoid blocking the loop.
        result: TestResultProcessor = await asyncio.to_thread(runner.run, suite)
        results = result.getTestResults()
        if self.__json_cache:
            await asyncio.to_thread(self.__saveCache, results)
        return results
