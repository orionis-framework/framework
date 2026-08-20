import asyncio
import contextlib
import fnmatch
import json
import os
import sys
import time
import unittest
from typing import Self, TYPE_CHECKING
from orionis.foundation.contracts.application import IApplication
from orionis.test.cases.case import TestCase
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.executors.runner import TestRunner
from orionis.test.executors.results import TestResultProcessor
from pathlib import Path

if TYPE_CHECKING:
    from collections.abc import Generator
    from orionis.test.entities.result import TestResult

class TestingEngine(ITestingEngine):

    # ruff: noqa: TC001

    def __init__(
        self,
        app: IApplication,
    ) -> None:
        """
        Initialize the TestingEngine with application configuration.

        Parameters
        ----------
        app : IApplication
            Application instance providing configuration values.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Retrieve configuration values from the application instance.
        self.__base_path: Path = app.basePath
        self.__verbosity: int = app.config("testing.verbosity")
        self.__fail_fast: bool = app.config("testing.fail_fast") in [
            1, True, "1", "true", "True",
        ]
        self.__start_dir: str = app.config("testing.start_dir")
        self.__file_pattern: str = app.config("testing.file_pattern")
        self.__method_pattern: str = app.config("testing.method_pattern")
        self.__json_cache: bool = app.config("testing.cache_results")
        self.__cache_folder: Path = (
            app.path("storage") / "framework" / "cache" / "testing"
        )
        self.__with_panel: bool = True  # Default to showing the start panel
        self.__suite: unittest.TestSuite = unittest.TestSuite()

    def setVerbosity(self, verbosity: int) -> Self:
        """
        Set the verbosity level for the testing engine.

        Parameters
        ----------
        verbosity : int
            Verbosity level to set.

        Returns
        -------
        Self
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
        Self
            Returns self for method chaining.
        """
        self.__fail_fast = fail_fast
        return self

    def setStartDir(self, start_dir: str) -> Self:
        """
        Set the start directory for test discovery.

        Parameters
        ----------
        start_dir : str
            Directory to start test discovery from.

        Returns
        -------
        Self
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
        Self
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
        Self
            Returns self for method chaining.
        """
        # Update the method pattern in TestCase to ensure
        # test methods are correctly identified.
        TestCase.setMethodPattern(method_pattern)

        # Update the method pattern in the engine for internal use.
        self.__method_pattern = method_pattern
        return self

    def withoutPanel(self) -> Self:
        """
        Disable the start panel display for the testing engine.

        Returns
        -------
        Self
            Returns self for method chaining.
        """
        self.__with_panel = False
        return self

    def __extractTests(
        self, test_suite: unittest.TestSuite,
    ) -> Generator[unittest.TestCase]:
        """
        Extract individual test cases from a test suite recursively.

        Parameters
        ----------
        test_suite : unittest.TestSuite
            Test suite to extract test cases from.

        Returns
        -------
        Generator[unittest.TestCase, None, None]
            Generator yielding individual test cases.
        """
        # Recursively extract test cases from nested suites.
        for test in test_suite:
            if isinstance(test, unittest.TestSuite):
                yield from self.__extractTests(test)
            else:
                yield test

    def discover(self) -> unittest.TestSuite:
        """
        Discover and filter tests using configuration parameters.

        Returns
        -------
        unittest.TestSuite
            Test suite containing filtered test cases.
        """
        # Ensure top-level directory is importable.
        top_level_dir: str = self.__base_path.absolute().as_posix()
        if top_level_dir not in sys.path:
            sys.path.insert(0, top_level_dir)

        start_dir_abs: Path = Path(self.__start_dir).resolve()

        # Use a fresh TestLoader to avoid shared state in defaultTestLoader.
        loader: unittest.TestLoader = unittest.TestLoader()
        filtered_suite: unittest.TestSuite = unittest.TestSuite()

        # Walk the entire directory tree so subdirectories without __init__.py
        # are also traversed (unittest.discover() skips them by default).
        for dirpath, _dirs, filenames in os.walk(start_dir_abs):
            for filename in filenames:
                if not fnmatch.fnmatch(filename, self.__file_pattern):
                    continue
                filepath = Path(dirpath) / filename
                rel = os.path.relpath(filepath.with_suffix(""), top_level_dir)
                module_name: str = rel.replace(os.sep, ".").replace("/", ".")
                # Any exception is possible when importing an arbitrary module
                # (SyntaxError, ImportError, NameError, …), so suppress broadly.
                with contextlib.suppress(Exception):
                    tests = loader.loadTestsFromName(module_name)
                    for test_case in self.__extractTests(tests):
                        method_name = getattr(test_case, "_testMethodName", None)
                        if method_name and fnmatch.fnmatch(
                            method_name, self.__method_pattern,
                        ):
                            filtered_suite.addTest(test_case)

        return filtered_suite

    async def __saveCache(self, results: list[TestResult]) -> None:
        """
        Save test results to a JSON cache file asynchronously.

        Parameters
        ----------
        results : list[TestResult]
            List of test results to save.

        Returns
        -------
        None
            This method does not return a value.
        """
        # If JSON caching is disabled, skip saving.
        if not self.__json_cache:
            return

        # Ensure the cache folder exists
        self.__cache_folder.mkdir(parents=True, exist_ok=True)

        data = [result.toDict() for result in results]
        timestamp = int(time.time())
        full_path = self.__cache_folder / f"{timestamp}.json"

        # Offload blocking file-write to a thread pool to keep the event loop free.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: full_path.write_text(
                json.dumps(data, indent=4, default=str),
                encoding="utf-8",
            ),
        )

    async def run(self) -> list[TestResult]:
        """
        Run the discovered test suite asynchronously.

        Adds discovered tests to the suite, sets verbosity, and executes the tests
        using a thread pool to avoid blocking. Saves results to cache if enabled.

        Returns
        -------
        list[TestResult]
            List of TestResult objects containing test execution outcomes.
        """
        # Add discovered tests to the suite.
        self.__suite.addTests(self.discover())

        # Set verbosity level in TestResult for output formatting.
        TestResultProcessor.setPrintVerbosity(self.__verbosity)

        # Create runner with current configuration.
        runner = TestRunner(
            verbosity=0,  # Keep at 0 to manage detail printing from TestResult.
            failfast=self.__fail_fast,
            with_panel=self.__with_panel,
        )

        # Offload the synchronous runner to a thread pool to avoid blocking the loop.
        loop = asyncio.get_running_loop()
        result: TestResultProcessor = await loop.run_in_executor(
            None, runner.run, self.__suite,
        )
        results = result.getTestResults()
        await self.__saveCache(results)
        return results
