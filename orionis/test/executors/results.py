import inspect
import linecache
import time
import traceback
import unittest
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from orionis.test.entities.result import TestResult
from orionis.test.enums.status import TestStatus

# Status-to-color mapping for Rich console output.
_STATUS_STYLE: dict[TestStatus, str] = {
    TestStatus.PASSED: "green",
    TestStatus.SKIPPED: "yellow",
    TestStatus.FAILED: "magenta",
    TestStatus.ERRORED: "red",
}

# Statuses that require detailed error rendering in verbosity=2 panels.
_FAILURE_STATUSES: frozenset[TestStatus] = frozenset({
    TestStatus.ERRORED,
    TestStatus.FAILED,
})

# Reusable Rich style strings for verbosity=2 panel content.
_V2_BOLD_WHITE: str = "bold bright_white"
_V2_DIM: str = "dim white"

class TestResultProcessor(unittest.TestResult):

    # ruff: noqa: PLR2004,PLW2901

    _print_verbosity: int | None = None

    @classmethod
    def setPrintVerbosity(cls, verbosity: int) -> None:
        """
        Set the print verbosity level for test result output.

        Parameters
        ----------
        verbosity : int
            The verbosity level to set for printing test results.

        Returns
        -------
        None
            This method sets a class-level attribute and returns None.
        """
        cls._print_verbosity = verbosity

    def __init__(self, *args: object, **kwargs: object) -> None:
        """
        Initialize the TestResultProcessor instance.

        Parameters
        ----------
        *args : object
            Positional arguments passed to the superclass.
        **kwargs : object
            Keyword arguments passed to the superclass.

        Returns
        -------
        None
            This constructor initializes instance attributes and returns None.
        """
        super().__init__(*args, **kwargs)
        self.__test_results: list[TestResult] = []
        self.__console = Console()
        self.__max_width = self.__console.width * 0.8

    def startTest(self, test: unittest.case.TestCase) -> None:
        """
        Start timing for a test case execution.

        Parameters
        ----------
        test : unittest.case.TestCase
            The test case instance being started.

        Returns
        -------
        None
            This method starts a timer and calls the superclass method.
        """
        self.__start_time = time.perf_counter()
        super().startTest(test)

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        """
        Record a successful test result and print it.

        Parameters
        ----------
        test : unittest.case.TestCase
            The test case instance that succeeded.

        Returns
        -------
        None
            This method appends the result and prints it, then calls the
            superclass method.
        """
        result = self.__createTestResult(test, TestStatus.PASSED)
        self.__test_results.append(result)
        self.__printTestResult(result)
        super().addSuccess(test)

    def addFailure(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, object],
    ) -> None:
        """
        Record a failed test result and print it.

        Parameters
        ----------
        test : unittest.case.TestCase
            The test case instance that failed.
        err : tuple[type[BaseException], BaseException, object]
            The exception info tuple for the failure.

        Returns
        -------
        None
            This method appends the result and prints it, then calls the
            superclass method.
        """
        result = self.__createTestResult(test, TestStatus.FAILED, err)
        self.__test_results.append(result)
        self.__printTestResult(result)
        super().addFailure(test, err)

    def addError(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, object],
    ) -> None:
        """
        Record an errored test result and print it.

        Parameters
        ----------
        test : unittest.case.TestCase
            The test case instance that errored.
        err : tuple[type[BaseException], BaseException, object]
            The exception info tuple for the error.

        Returns
        -------
        None
            This method appends the result and prints it, then calls the
            superclass method.
        """
        result = self.__createTestResult(test, TestStatus.ERRORED, err)
        self.__test_results.append(result)
        self.__printTestResult(result)
        super().addError(test, err)

    def addSkip(
        self,
        test: unittest.case.TestCase,
        reason: str,
    ) -> None:
        """
        Record a skipped test result and print it.

        Parameters
        ----------
        test : unittest.case.TestCase
            The test case instance that was skipped.
        reason : str
            The reason for skipping the test.

        Returns
        -------
        None
            This method appends the result and prints it, then calls the
            superclass method.
        """
        result = self.__createTestResult(test, TestStatus.SKIPPED)
        self.__test_results.append(result)
        self.__printTestResult(result)
        super().addSkip(test, reason)

    def __printTestResult(self, result: TestResult) -> None: # NOSONAR
        """
        Print the result of a test that did not fail.

        Parameters
        ----------
        result : TestResult
            The test result instance to display.

        Returns
        -------
        None
            This method prints the formatted test result to the console and
            does not return a value.
        """
        # Resolve status style and format status label centered in a fixed-width cell.
        status_style: str = _STATUS_STYLE.get(result.status, "white")
        status_text: str = result.status.center(9)
        test_id: str = result.name
        exec_time_text: str = f"~ {result.execution_time:.3f}s"

        # Read verbosity once to avoid repeated class-level lookup.
        verbosity: int | None = self._print_verbosity

        # Compact single-line output with dot-filler alignment.
        if verbosity == 1:

            # Calculate filler length for formatting.
            max_width: int = int(self.__max_width)
            status_len: int = len(status_text)
            test_id_len: int = len(test_id)
            exec_time_len: int = len(exec_time_text)

            # Length for separators and spaces.
            separator_len: int = 6

            # Compute dot-filler length so the line fits within max_width.
            natural_filler: int = (
                max_width - status_len - test_id_len - exec_time_len - separator_len
            )

            if natural_filler < 0:
                # Truncate test name to fit within max width, leaving room for "...".
                max_test_id_len = max(
                    0,
                    max_width - status_len - exec_time_len - separator_len - 3,
                )
                test_id = test_id[:max_test_id_len] + "..."
                filler_length = 0
            else:
                filler_length = natural_filler

            filler: str = "." * filler_length

            # Assemble with tuples to avoid allocating intermediate Text objects.
            formatted_text: Text = Text.assemble(
                (status_text, f"bold white on {status_style}"),
                (" • ", "dim"),
                (test_id, "white"),
                (" ", "dim"),
                (filler, "dim"),
                (" • ", "dim"),
                (exec_time_text, "cyan"),
            )

            # Output formatted test result to console.
            self.__console.print(formatted_text)

        elif verbosity == 2:

            # Build the path segment; failures append the line number.
            text_path = Text(f"📄 Path: {result.file_path}")
            other_texts: list[Text] = []
            if result.status in _FAILURE_STATUSES:
                icon = "❌" if result.status == TestStatus.FAILED else "💥"
                text_path = Text(
                    f"📄 Path: {result.file_path}:{result.line_no}", style="cyan",
                )
                other_texts.append(
                    Text(
                        f"\n{icon} {result.exception}: {result.error_message}\n",
                        style="red",
                    ),
                )
                for line_no, code_line in result.source_code:
                    code_line = (
                        code_line[:70] + "..."
                        if len(code_line) > 73
                        else code_line
                    )
                    if line_no == result.line_no:
                        other_texts.append(
                            Text(
                                f"\n *| {line_no}: {code_line}",
                                style="white on grey23",
                            ),
                        )
                    else:
                        other_texts.append(
                            Text(
                                f"\n  | {line_no}: {code_line}",
                                style="dim white",
                            ),
                        )

            # Render a detailed panel with test metadata and optional error context.
            panel = Panel(
                Text.assemble(
                    ("🔑 ", ""),
                    ("ID: ", _V2_BOLD_WHITE),
                    (f"{result.id}", _V2_DIM),
                    (" | ", _V2_DIM),
                    ("📌 ", ""),
                    ("Name: ", _V2_BOLD_WHITE),
                    (f"{result.name}", _V2_DIM),
                    ("\n", ""),
                    ("📁 ", ""),
                    ("Class: ", _V2_BOLD_WHITE),
                    (f"{result.class_name}", _V2_DIM),
                    (" | ", _V2_DIM),
                    ("🔧 ", ""),
                    ("Method: ", _V2_BOLD_WHITE),
                    (f"{result.method}", _V2_DIM),
                    (" | ", _V2_DIM),
                    ("📦 ", ""),
                    ("Module: ", _V2_BOLD_WHITE),
                    (f"{result.module}", _V2_DIM),
                    ("\n", ""),
                    text_path,
                    *other_texts,
                ),
                title=result.status,
                title_align="left",
                subtitle=exec_time_text,
                subtitle_align="right",
                border_style=f"bright_{status_style}",
                width=int(self.__max_width * 0.85),
                padding=(0, 1),
            )
            self.__console.print(panel)

    def __extractTraceInfo(
        self,
        exc_info: tuple[type[BaseException], BaseException, object],
        file_path: str | None,
    ) -> tuple[list[str], list[tuple[int, str]], int | None]:
        """
        Extract formatted traceback and highlighted source lines for a test failure.

        Parameters
        ----------
        exc_info : tuple
            Exception info tuple as returned by sys.exc_info().
        file_path : str or None
            Absolute path of the test source file used to filter stack frames.

        Returns
        -------
        tuple
            A three-element tuple of (traceback_lines, source_code_pairs, line_no).
        """
        # Format the full exception traceback as a list of strings.
        _traceback: list[str] = traceback.format_exception(*exc_info)
        _code: list[tuple[int, str]] = []
        line_no: int | None = None

        # Scan the call stack for frames that belong to the test source file.
        if file_path:
            for exc in inspect.trace():
                frame = exc.frame
                lineno = exc.lineno
                if file_path in frame.f_code.co_filename:
                    filename = frame.f_code.co_filename
                    start = max(1, lineno - 2)
                    end = lineno + 1
                    line_no = lineno
                    for i in range(start, end + 1):
                        code_line = linecache.getline(filename, i).rstrip()
                        _code.append((i, code_line))

        return _traceback, _code, line_no

    def __createTestResult(
        self,
        test: unittest.case.TestCase,
        status: TestStatus,
        exc_info: tuple[type[BaseException], BaseException, object] | None = None,
    ) -> TestResult:
        """
        Create and return a TestResult instance for the given test.

        Parameters
        ----------
        test : unittest.case.TestCase
            The test case instance being processed.
        status : TestStatus
            The status of the test (e.g., PASSED, FAILED).
        exc_info : tuple[type[BaseException], BaseException, object] or None, optional
            Exception info tuple as returned by sys.exc_info(), by default None.

        Returns
        -------
        TestResult
            The constructed TestResult object containing test outcome details.
        """
        # Measure elapsed time and extract class metadata from the test instance.
        elapsed: float = time.perf_counter() - self.__start_time
        cls = type(test)
        method_name: str | None = getattr(test, "_testMethodName", None)

        # Resolve the source file path without creating a full ReflectionInstance.
        try:
            file_path: str | None = inspect.getfile(cls)
        except (TypeError, OSError):
            file_path = None

        # Delegate traceback extraction to a focused helper to contain complexity.
        _traceback = None
        _code: list[tuple[int, str]] = []
        line_no: int | None = None
        if exc_info:
            _traceback, _code, line_no = self.__extractTraceInfo(exc_info, file_path)

        # Retrieve the actual test method docstring from the class.
        test_method_fn = getattr(cls, method_name, None) if method_name else None
        doc_string: str | None = (
            inspect.getdoc(test_method_fn) if test_method_fn is not None else None
        )

        # Construct and return the TestResult with metadata resolved via direct access.
        return TestResult(
            id=id(test),
            name=test.id(),
            status=status,
            execution_time=elapsed,
            error_message=str(exc_info[1]) if exc_info else None,
            traceback=_traceback,
            class_name=cls.__name__,
            method=method_name,
            module=cls.__module__,
            file_path=file_path,
            doc_string=doc_string,
            exception=exc_info[0].__name__ if exc_info else None,
            line_no=line_no,
            source_code=_code,
        )

    def getTestResults(self) -> list[TestResult]:
        """
        Retrieve the list of test results collected during execution.

        Returns
        -------
        list[TestResult]
            A list of TestResult instances representing the outcomes of
            executed tests.
        """
        return self.__test_results
