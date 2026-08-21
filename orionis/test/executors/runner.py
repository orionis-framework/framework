import asyncio
import os
import time
from typing import TYPE_CHECKING
import unittest
import warnings
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from orionis.support.facades.datetime import DateTime
from orionis.test.enums.status import TestStatus
from orionis.test.executors.results import TestResultProcessor

if TYPE_CHECKING:
    from orionis.test.entities.result import TestResult

class TestRunner(unittest.TextTestRunner):

    # ruff: noqa: FBT001, FBT002

    resultclass = TestResultProcessor

    def __init__(
        self,
        verbosity: int = 0,
        failfast: bool = False,
        buffer: bool = False,
        warnings: str | None = None,
        with_panel: bool = True,
        **kwargs: dict,
    ) -> None:
        """
        Initialize the test runner with custom settings.

        Parameters
        ----------
        verbosity : int, optional
            Level of detail printed for each test. It is handed to the
            TestResultProcessor built by _makeResult, which owns the console
            rendering: 1 prints one line per test, 2 prints a detailed panel
            and any other value prints nothing, by default 0
        failfast : bool, optional
            Stop on first failure, by default False
        buffer : bool, optional
            Buffer stdout and stderr during tests, by default False
        warnings : str | None, optional
            Control warnings during test execution, by default None
        with_panel : bool, optional
            Render the Rich start and summary panels around the run. When
            False both panels are skipped and the console is never cleared,
            by default True
        **kwargs : dict
            Additional keyword arguments forwarded verbatim to
            unittest.TextTestRunner (stream, descriptions, tb_locals,
            durations), whose semantics are defined by the standard library.

        Returns
        -------
        None
            This constructor initializes the instance and returns None.
        """
        # Call the parent constructor with provided arguments
        super().__init__(
            verbosity=verbosity,
            failfast=failfast,
            buffer=buffer,
            warnings=warnings,
            **kwargs,
        )

        # Initialize a Rich console for output
        self.__console: Console = Console()
        self.__with_panel: bool = with_panel

    def __startPanel(self) -> None:
        """
        Display the test suite start panel using Rich.

        Initializes and renders a Rich panel to indicate the start of the test
        suite execution, including server status, start time, process ID, and
        event loop policy.

        Returns
        -------
        None
            This method performs output and does not return a value.
        """
        # Clear previous output and add spacing
        self.__console.clear()
        self.__console.line()

        # Get the current time and process ID for display in the panel
        now: str = DateTime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Get the current process ID for display in the panel
        pid: int = os.getpid()

        # Get the current event loop policy to display in the panel
        policy_cls = asyncio.DefaultEventLoopPolicy
        loop_name = f"{policy_cls.__module__}.{policy_cls.__name__}"\
                    .title()\
                    .replace("Asyncio", "AsyncIO")\
                    .replace("_", "")\
                    .replace("event", "Event")\
                    .replace("proactor", "Proactor")\
                    .replace("policy", "Policy")\
                    .replace("loop", "Loop")

        # Build the panel content for server status
        panel_content: Text = Text.assemble(
            (" 🚀 Orionis TestSuite \n\n", "bold white on green"),
            (f"🕒 Started at: {now}   ", "dim"),
            (f"🆔 PID: {pid}\n", "dim"),
            ("⚡ Reactor Loop Policy: ", "cyan"),
            (f"{loop_name}\n", "bold magenta"),
            ("🛑 To stop the server, press ", "white"),
            ("Ctrl+C", "bold yellow"),
        )

        # Render the status panel to the console.
        self.__console.print(
            Panel(
                panel_content,
                border_style="green",
                padding=(1, 2),
            ),
        )
        self.__console.line()

    def __endPanel(
        self, test_result: list[TestResult], time_taken: float,
    ) -> None:
        """
        Display the test summary panel using Rich.

        Summarize and render the results of the test suite execution, including
        counts for each test status and total execution time.

        Parameters
        ----------
        test_result : list[TestResult]
            List of test result objects to summarize.
        time_taken : float
            Total time taken to execute the test suite.

        Returns
        -------
        None
            This method performs output and does not return a value.
        """
        # Print a blank line before displaying results.
        self.__console.line()

        # Gather and summarize test results.
        status_counts = {
            TestStatus.PASSED: 0,
            TestStatus.FAILED: 0,
            TestStatus.ERRORED: 0,
            TestStatus.SKIPPED: 0,
        }
        for _test in test_result:
            if _test.status in status_counts:
                status_counts[_test.status] += 1

        total_tests = len(test_result)
        passed = status_counts[TestStatus.PASSED]
        failed = status_counts[TestStatus.FAILED]
        errored = status_counts[TestStatus.ERRORED]
        skipped = status_counts[TestStatus.SKIPPED]

        # Display summary table.
        table = Table(
            show_header=True,
            header_style="bold white on green",
            border_style="green",
            min_width=self.__console.width / 2,
            caption=f"Total execution time: {time_taken:.3f} seconds",
        )
        table.add_column("Total", justify="center")
        table.add_column("Passed", justify="center")
        table.add_column("Failed", justify="center")
        table.add_column("Errored", justify="center")
        table.add_column("Skipped", justify="center")

        table.add_row(
            str(total_tests),
            str(passed),
            str(failed),
            str(errored),
            str(skipped),
        )
        self.__console.print(table)

    def run(self, test: unittest.suite.TestSuite) -> unittest.result.TestResult:
        """
        Execute the given test suite or test case.

        Parameters
        ----------
        test : unittest.suite.TestSuite
            The test case or suite to execute.

        Returns
        -------
        unittest.result.TestResult
            The result object containing test execution details.
        """
        # Display the start panel before running tests.
        if self.__with_panel:
            self.__startPanel()

        # Create a result object to store test execution results.
        result: unittest.result.TestResult = self._makeResult()
        unittest.registerResult(result)

        # Set result attributes based on runner configuration.
        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals

        # Handle warnings as configured.
        with warnings.catch_warnings():
            if self.warnings:
                warnings.simplefilter(self.warnings)

            # Start timer to measure test execution duration.
            start_time: float = time.perf_counter()

            # Invoke optional lifecycle hooks directly via getattr.
            start_test_run = getattr(result, "startTestRun", None)
            if start_test_run is not None:
                start_test_run()

            # Execute the test and ensure cleanup.
            try:
                test(result)
            finally:
                stop_test_run = getattr(result, "stopTestRun", None)
                if stop_test_run is not None:
                    stop_test_run()

            # Stop timer after test execution.
            stop_time: float = time.perf_counter()

        # Calculate total execution time.
        time_taken: float = stop_time - start_time

        # Render the summary panel using results collected by the processor.
        test_result_callback = getattr(result, "getTestResults", None)
        if callable(test_result_callback) and self.__with_panel:
            self.__endPanel(test_result_callback(), time_taken)

        # Print a blank line after results only if the panel is not shown.
        if self.__with_panel:
            self.__console.line()

        # Return the result object containing test execution details.
        return result
