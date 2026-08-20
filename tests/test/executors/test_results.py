import io
import json
from typing import TYPE_CHECKING
from rich.console import Console
from orionis.test import TestCase
from orionis.test.cases.case import TestCase as CoreTestCase
from orionis.test.enums.status import TestStatus
from orionis.test.executors.results import TestResultProcessor

if TYPE_CHECKING:
    from orionis.test.entities.result import TestResult

# Module name used to simulate a class whose source file cannot be resolved.
_MISSING_MODULE: str = "_orionis_missing_module"

def _probe_test(_self: object) -> None:
    """Describe the probe method used as the subject of a report."""

def _make_case(*, module: str | None = None) -> CoreTestCase:
    """Create a test case instance used as the subject of a report."""
    probe = type("_ProbeCase", (CoreTestCase,), {"testProbe": _probe_test})
    if module is not None:
        probe.__module__ = module
    return probe("testProbe")

def _raise_failure() -> None:
    """Raise an assertion error from a known source line."""
    error_msg = "probe failure"
    # A deliberately long comment line used to exercise the source code trimming
    raise AssertionError(error_msg)

def _raise_error() -> None:
    """Raise a runtime error from a known source line."""
    error_msg = "probe error"
    raise RuntimeError(error_msg)

def _bind_console(processor: TestResultProcessor, width: int) -> io.StringIO:
    """Redirect the processor console to an in-memory buffer."""
    buffer = io.StringIO()
    processor._TestResultProcessor__console = Console(file=buffer, width=width)
    processor._TestResultProcessor__max_width = width * 0.8
    return buffer

class _ProcessorTestCase(TestCase):
    """Base scenario providing processors bound to an in-memory console."""

    def setUp(self) -> None:
        """
        Capture the shared reporting verbosity before each scenario.

        Guarantees that console output of the surrounding run is not
        affected by the verbosity levels exercised here.
        """
        self._verbosity = TestResultProcessor._print_verbosity

    def tearDown(self) -> None:
        """
        Restore the shared reporting verbosity after each scenario.

        Prevents class level state from leaking into the tests executed
        afterwards.
        """
        TestResultProcessor._print_verbosity = self._verbosity

    def _makeProcessor(self, width: int = 120) -> TestResultProcessor:
        """Build a processor writing to an in-memory console."""
        processor = TestResultProcessor()
        self._buffer = _bind_console(processor, width)
        return processor

    def _output(self) -> str:
        """Return everything rendered by the in-memory console."""
        return self._buffer.getvalue()

    def _addSuccess(self, processor: TestResultProcessor) -> TestResult:
        """Record a successful outcome and return the produced report."""
        case = _make_case()
        processor.startTest(case)
        processor.addSuccess(case)
        return processor.getTestResults()[-1]

    def _addOutcome(
        self,
        processor: TestResultProcessor,
        *,
        errored: bool,
        module: str | None = None,
    ) -> TestResult:
        """Record a failing outcome and return the produced report."""
        case = _make_case(module=module)
        raiser = _raise_error if errored else _raise_failure
        record = processor.addError if errored else processor.addFailure
        processor.startTest(case)
        try:
            raiser()
        except (AssertionError, RuntimeError) as exc:
            record(case, (type(exc), exc, exc.__traceback__))
        return processor.getTestResults()[-1]

class TestTestResultProcessorDefinition(_ProcessorTestCase):

    def testDerivesFromStandardTestResult(self) -> None:
        """
        Derive from the result collector of the standard library.

        Validates that the processor can be plugged into any standard
        runner.
        """
        ancestors = [base.__name__ for base in TestResultProcessor.__mro__]
        self.assertIn("TestResult", ancestors)

    def testFreshProcessorHoldsNoResult(self) -> None:
        """
        Start with an empty report collection.

        Validates that a processor never inherits results from a
        previous run.
        """
        self.assertEqual(self._makeProcessor().getTestResults(), [])

    def testResultCollectionIsStable(self) -> None:
        """
        Return the very same collection on consecutive reads.

        Validates that callers can hold a reference to the growing
        report list.
        """
        processor = self._makeProcessor()
        self.assertIs(processor.getTestResults(), processor.getTestResults())

    def testPrintVerbosityIsStored(self) -> None:
        """
        Store the requested reporting verbosity at class level.

        Validates the switch used by the engine to control console
        output detail.
        """
        for verbosity in (0, 1, 2):
            TestResultProcessor.setPrintVerbosity(verbosity)
            self.assertEqual(TestResultProcessor._print_verbosity, verbosity)

class TestTestResultProcessorOutcomes(_ProcessorTestCase):

    def setUp(self) -> None:
        """
        Silence the console before recording outcomes.

        Guarantees that outcome scenarios assert on the produced reports
        rather than on rendered text.
        """
        super().setUp()
        TestResultProcessor.setPrintVerbosity(0)

    def testSuccessIsRecorded(self) -> None:
        """
        Record a passed report for a successful test.

        Validates the outcome published for tests that raise nothing.
        """
        processor = self._makeProcessor()
        result = self._addSuccess(processor)
        self.assertEqual(result.status, TestStatus.PASSED)
        self.assertEqual(processor.testsRun, 1)

    def testSuccessCarriesTestMetadata(self) -> None:
        """
        Describe the executed test in the produced report.

        Validates that identity, location and documentation are captured
        for later reporting.
        """
        result = self._addSuccess(self._makeProcessor())
        self.assertEqual(result.class_name, "_ProbeCase")
        self.assertEqual(result.method, "testProbe")
        self.assertEqual(result.module, __name__)
        self.assertEqual(result.doc_string, _probe_test.__doc__)
        self.assertIn("test_results.py", str(result.file_path))

    def testSuccessCarriesNoDiagnostics(self) -> None:
        """
        Leave the failure diagnostics empty for a successful test.

        Validates that no traceback is attached when nothing went wrong.
        """
        result = self._addSuccess(self._makeProcessor())
        self.assertIsNone(result.error_message)
        self.assertIsNone(result.traceback)
        self.assertIsNone(result.exception)
        self.assertIsNone(result.line_no)
        self.assertEqual(result.source_code, [])

    def testExecutionTimeIsMeasured(self) -> None:
        """
        Measure the elapsed time between start and outcome.

        Validates that the reported duration is a non negative number.
        """
        result = self._addSuccess(self._makeProcessor())
        self.assertGreaterEqual(result.execution_time, 0.0)

    def testFailureIsRecorded(self) -> None:
        """
        Record a failed report for a broken assertion.

        Validates the outcome published when a test assertion does not
        hold.
        """
        processor = self._makeProcessor()
        result = self._addOutcome(processor, errored=False)
        self.assertEqual(result.status, TestStatus.FAILED)
        self.assertEqual(len(processor.failures), 1)

    def testFailureCarriesDiagnostics(self) -> None:
        """
        Attach the exception details of a failed test.

        Validates that message, exception name and traceback reach the
        report.
        """
        result = self._addOutcome(self._makeProcessor(), errored=False)
        self.assertEqual(result.error_message, "probe failure")
        self.assertEqual(result.exception, "AssertionError")
        self.assertIsInstance(result.traceback, list)

    def testFailureCarriesSourceContext(self) -> None:
        """
        Attach the source lines surrounding a failed assertion.

        Validates that the highlighted line belongs to the captured
        source excerpt.
        """
        result = self._addOutcome(self._makeProcessor(), errored=False)
        self.assertIsNotNone(result.line_no)
        self.assertIn(result.line_no, [line for line, _code in result.source_code])

    def testErrorIsRecorded(self) -> None:
        """
        Record an errored report for an unexpected exception.

        Validates the outcome published when a test raises something
        other than an assertion error.
        """
        processor = self._makeProcessor()
        result = self._addOutcome(processor, errored=True)
        self.assertEqual(result.status, TestStatus.ERRORED)
        self.assertEqual(result.exception, "RuntimeError")
        self.assertEqual(len(processor.errors), 1)

    def testSkipIsRecorded(self) -> None:
        """
        Record a skipped report together with its reason.

        Validates that intentionally ignored tests are still published
        in the report.
        """
        processor = self._makeProcessor()
        case = _make_case()
        processor.startTest(case)
        processor.addSkip(case, "not applicable")
        self.assertEqual(processor.getTestResults()[-1].status, TestStatus.SKIPPED)
        self.assertEqual(processor.skipped[0][1], "not applicable")

    def testResultsArePublishedInExecutionOrder(self) -> None:
        """
        Publish every recorded outcome in execution order.

        Validates that the report collection mirrors the order in which
        tests ran.
        """
        processor = self._makeProcessor()
        self._addSuccess(processor)
        self._addOutcome(processor, errored=False)
        self._addOutcome(processor, errored=True)
        statuses = [result.status for result in processor.getTestResults()]
        self.assertEqual(
            statuses,
            [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERRORED],
        )

    def testForeignStackFramesAreIgnored(self) -> None:
        """
        Ignore stack frames that do not belong to the test source file.

        Validates that the reported excerpt always points at the test
        itself instead of third party code.
        """
        processor = self._makeProcessor()
        case = _make_case()
        processor.startTest(case)
        try:
            json.loads("{")
        except ValueError as exc:
            processor.addError(case, (type(exc), exc, exc.__traceback__))
        result = processor.getTestResults()[-1]
        self.assertEqual(result.exception, "JSONDecodeError")
        self.assertTrue(
            any("json.loads" in code for _line, code in result.source_code),
        )

    def testUnresolvableSourceFileIsTolerated(self) -> None:
        """
        Publish a report even when the source file cannot be resolved.

        Validates that classes without an importable module never break
        the reporting pipeline.
        """
        result = self._addOutcome(
            self._makeProcessor(), errored=False, module=_MISSING_MODULE,
        )
        self.assertIsNone(result.file_path)
        self.assertIsNone(result.line_no)
        self.assertEqual(result.source_code, [])

    def testMissingMethodNameIsTolerated(self) -> None:
        """
        Publish a report when the test exposes no resolvable method.

        Validates that documentation extraction degrades gracefully for
        synthetic test objects.
        """
        processor = self._makeProcessor()
        case = _make_case()
        case._testMethodName = ""
        processor.startTest(case)
        processor.addSuccess(case)
        result = processor.getTestResults()[-1]
        self.assertEqual(result.method, "")
        self.assertIsNone(result.doc_string)

class TestTestResultProcessorDefaultRendering(_ProcessorTestCase):

    def setUp(self) -> None:
        """
        Reset the reporting verbosity to its unconfigured state.

        Reproduces a processor used directly, without the engine having
        published a verbosity level.
        """
        super().setUp()
        TestResultProcessor._print_verbosity = None

    def testUnsetVerbosityRendersNothing(self) -> None:
        """
        Render no output when no reporting verbosity was configured.

        Validates the default behaviour of a processor used outside the
        engine.
        """
        self._addSuccess(self._makeProcessor())
        self.assertEqual(self._output(), "")

class TestTestResultProcessorRendering(_ProcessorTestCase):

    def testSilentVerbosityRendersNothing(self) -> None:
        """
        Render no output when the reporting verbosity is silent.

        Validates that embedded runs can execute without touching the
        console.
        """
        TestResultProcessor.setPrintVerbosity(0)
        self._addSuccess(self._makeProcessor())
        self.assertEqual(self._output(), "")

    def testCompactVerbosityRendersASingleLine(self) -> None:
        """
        Render one aligned line per test at compact verbosity.

        Validates the summary format used during regular runs.
        """
        TestResultProcessor.setPrintVerbosity(1)
        result = self._addSuccess(self._makeProcessor())
        output = self._output()
        self.assertIn("PASSED", output)
        self.assertIn(result.name, output)
        self.assertIn("..", output)

    def testCompactVerbosityTruncatesLongNames(self) -> None:
        """
        Truncate the test name when the line does not fit.

        Validates that narrow consoles never produce wrapped summary
        lines.
        """
        TestResultProcessor.setPrintVerbosity(1)
        result = self._addSuccess(self._makeProcessor(width=40))
        output = self._output()
        self.assertIn("...", output)
        self.assertNotIn(result.name, output)

    def testDetailedVerbosityRendersAPanel(self) -> None:
        """
        Render a metadata panel per test at detailed verbosity.

        Validates the diagnostic format used while investigating a run.
        """
        TestResultProcessor.setPrintVerbosity(2)
        self._addSuccess(self._makeProcessor())
        output = self._output()
        self.assertIn("ID:", output)
        self.assertIn("Class:", output)
        self.assertIn("Path:", output)
        self.assertNotIn("❌", output)

    def testDetailedVerbosityRendersFailureContext(self) -> None:
        """
        Render the failing line and its neighbours for a failed test.

        Validates that the panel highlights the offending statement and
        trims overly long source lines.
        """
        TestResultProcessor.setPrintVerbosity(2)
        self._addOutcome(self._makeProcessor(), errored=False)
        output = self._output()
        self.assertIn("❌", output)
        self.assertIn("AssertionError", output)
        self.assertIn("*|", output)
        self.assertIn("...", output)

    def testDetailedVerbosityRendersErrorContext(self) -> None:
        """
        Render a distinct marker for an errored test.

        Validates that unexpected exceptions are visually separated from
        assertion failures.
        """
        TestResultProcessor.setPrintVerbosity(2)
        self._addOutcome(self._makeProcessor(), errored=True)
        output = self._output()
        self.assertIn("💥", output)
        self.assertIn("RuntimeError", output)
