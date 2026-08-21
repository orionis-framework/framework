from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Self, TYPE_CHECKING

if TYPE_CHECKING:
    import unittest
    from orionis.test.entities.result import TestResult

class ITestingEngine(ABC):

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def withoutPanel(self) -> Self:
        """
        Disable the start panel display for the testing engine.

        Returns
        -------
        Self
            Returns self for method chaining.
        """

    @abstractmethod
    def discover(self) -> unittest.TestSuite:
        """
        Discover and filter tests using configuration parameters.

        Returns
        -------
        unittest.TestSuite
            Test suite containing filtered test cases.
        """

    @abstractmethod
    async def run(self) -> list[TestResult]:
        """
        Run the discovered test suite asynchronously.

        Discovers the tests, sets verbosity, and executes them using a thread
        pool to avoid blocking. Saves results to cache if enabled.

        Returns
        -------
        list[TestResult]
            List of TestResult objects containing test execution outcomes.
        """
