import io
from rich.console import Console
from orionis.test import TestCase
from orionis.test.cases.case import TestCase as CoreTestCase
from orionis.test.enums.status import TestStatus
from orionis.test.executors.results import TestResultProcessor
from orionis.test.executors.runner import TestRunner

# Message raised by the suite double used to check cleanup handling.
_SUITE_FAILURE: str = "suite exploded"

def _probe_test(_self: object) -> None:
    """Describe the probe method used as the subject of a report."""

def _make_case() -> CoreTestCase:
    """Create a test case instance used as the subject of a report."""
    probe = type("_ProbeCase", (CoreTestCase,), {"testProbe": _probe_test})
    return probe("testProbe")

def _bind_console(runner: TestRunner, width: int = 120) -> io.StringIO:
    """Redirect the runner console to an in-memory buffer."""
    buffer = io.StringIO()
    runner._TestRunner__console = Console(file=buffer, width=width)
    return buffer

class _StubSuite:
    """Suite double feeding predefined outcomes into a result object."""

    __slots__ = ("case", "statuses")

    def __init__(self, statuses: tuple[TestStatus, ...] = ()) -> None:
        self.case = _make_case()
        self.statuses = statuses

    def __call__(self, result: TestResultProcessor) -> None:
        """Report every predefined outcome to the given result object."""
        for status in self.statuses:
            result.startTest(self.case)
            self._report(result, status)
            result.stopTest(self.case)

    def _report(self, result: TestResultProcessor, status: TestStatus) -> None:
        """Publish a single outcome matching the requested status."""
        if status is TestStatus.PASSED:
            result.addSuccess(self.case)
        elif status is TestStatus.SKIPPED:
            result.addSkip(self.case, "not applicable")
        else:
            try:
                raise RuntimeError(_SUITE_FAILURE)
            except RuntimeError as exc:
                info = (type(exc), exc, exc.__traceback__)
                if status is TestStatus.FAILED:
                    result.addFailure(self.case, info)
                else:
                    result.addError(self.case, info)

class _ExplodingSuite:
    """Suite double raising while it is executed by the runner."""

    __slots__ = ()

    def __call__(self, _result: TestResultProcessor) -> None:
        """Raise unconditionally to exercise the cleanup path."""
        raise RuntimeError(_SUITE_FAILURE)

class _RunnerTestCase(TestCase):
    """Base scenario keeping the reporting verbosity under control."""

    def setUp(self) -> None:
        """
        Silence the result processor before each scenario.

        Guarantees that nested runs never write to the console of the
        surrounding test session.
        """
        self._verbosity = TestResultProcessor._print_verbosity
        TestResultProcessor.setPrintVerbosity(0)

    def tearDown(self) -> None:
        """
        Restore the reporting verbosity after each scenario.

        Prevents class level state from leaking into the tests executed
        afterwards.
        """
        TestResultProcessor._print_verbosity = self._verbosity

    def _run(self, runner: TestRunner, suite: object) -> TestResultProcessor:
        """Execute a suite double and return the produced result object."""
        return runner.run(suite)  # type: ignore[arg-type]

class TestTestRunnerDefinition(_RunnerTestCase):

    def testDerivesFromTextTestRunner(self) -> None:
        """
        Derive from the textual runner of the standard library.

        Validates that the standard execution protocol is preserved.
        """
        ancestors = [base.__name__ for base in TestRunner.__mro__]
        self.assertIn("TextTestRunner", ancestors)

    def testUsesTheProcessorAsResultClass(self) -> None:
        """
        Collect results through the Orionis result processor.

        Validates that live reporting is enabled for every run.
        """
        self.assertIs(TestRunner.resultclass, TestResultProcessor)

    def testDefaultConfigurationIsSilent(self) -> None:
        """
        Default to silent output without early exit.

        Validates that detail printing is delegated to the result
        processor instead of the runner.
        """
        runner = TestRunner()
        self.assertEqual(runner.verbosity, 0)
        self.assertFalse(runner.failfast)
        self.assertFalse(runner.buffer)

    def testStartPanelIsEnabledByDefault(self) -> None:
        """
        Enable the start panel unless it is explicitly disabled.

        Validates the default presentation behaviour of the runner.
        """
        self.assertIs(TestRunner()._TestRunner__with_panel, True)

    def testExplicitConfigurationIsStored(self) -> None:
        """
        Store every option supplied at construction time.

        Validates that the engine can fully configure the underlying
        runner.
        """
        runner = TestRunner(
            verbosity=2,
            failfast=True,
            buffer=True,
            warnings="ignore",
            with_panel=False,
        )
        self.assertEqual(runner.verbosity, 2)
        self.assertTrue(runner.failfast)
        self.assertTrue(runner.buffer)
        self.assertEqual(runner.warnings, "ignore")
        self.assertIs(runner._TestRunner__with_panel, False)

class TestTestRunnerExecution(_RunnerTestCase):

    def testRunReturnsTheResultProcessor(self) -> None:
        """
        Return the processor holding every recorded outcome.

        Validates the contract consumed by the testing engine.
        """
        runner = TestRunner(with_panel=False)
        result = self._run(runner, _StubSuite((TestStatus.PASSED,)))
        self.assertIsInstance(result, TestResultProcessor)
        self.assertEqual(len(result.getTestResults()), 1)

    def testRunPropagatesRunnerConfigurationToTheResult(self) -> None:
        """
        Publish the runner configuration on the result object.

        Validates that fail fast and output buffering reach the
        collector.
        """
        runner = TestRunner(failfast=True, buffer=True, with_panel=False)
        result = self._run(runner, _StubSuite())
        self.assertTrue(result.failfast)
        self.assertTrue(result.buffer)

    def testRunAcceptsAWarningFilter(self) -> None:
        """
        Execute the suite under the configured warning filter.

        Validates that the optional warning policy does not disturb the
        execution flow.
        """
        runner = TestRunner(warnings="ignore", with_panel=False)
        result = self._run(runner, _StubSuite((TestStatus.PASSED,)))
        self.assertEqual(len(result.getTestResults()), 1)

    def testRunWithoutPanelsRendersNothing(self) -> None:
        """
        Render no decorative output when panels are disabled.

        Validates that embedded runs keep the console untouched.
        """
        runner = TestRunner(with_panel=False)
        buffer = _bind_console(runner)
        self._run(runner, _StubSuite((TestStatus.PASSED,)))
        self.assertEqual(buffer.getvalue(), "")

    def testRunPropagatesSuiteFailures(self) -> None:
        """
        Propagate an exception raised while the suite executes.

        Validates that infrastructure errors are never swallowed by the
        runner.
        """
        runner = TestRunner(with_panel=False)
        with self.assertRaises(RuntimeError):
            self._run(runner, _ExplodingSuite())

class TestTestRunnerPanels(_RunnerTestCase):

    def testStartPanelDescribesTheSession(self) -> None:
        """
        Render the session banner before the suite executes.

        Validates that the start panel reports the running process.
        """
        runner = TestRunner()
        buffer = _bind_console(runner)
        self._run(runner, _StubSuite())
        output = buffer.getvalue()
        self.assertIn("Orionis TestSuite", output)
        self.assertIn("PID:", output)

    def testSummaryPanelCountsEveryStatus(self) -> None:
        """
        Summarise the outcome of the whole suite once it finishes.

        Validates that each status is counted separately in the final
        table.
        """
        runner = TestRunner()
        buffer = _bind_console(runner)
        self._run(
            runner,
            _StubSuite((
                TestStatus.PASSED,
                TestStatus.FAILED,
                TestStatus.ERRORED,
                TestStatus.SKIPPED,
            )),
        )
        output = buffer.getvalue()
        self.assertIn("Total", output)
        self.assertIn("Passed", output)
        self.assertIn("Skipped", output)
        self.assertIn("Total execution time", output)

    def testSummaryPanelHandlesAnEmptySuite(self) -> None:
        """
        Summarise a run that executed no test at all.

        Validates that the final table degrades gracefully instead of
        raising.
        """
        runner = TestRunner()
        buffer = _bind_console(runner)
        self._run(runner, _StubSuite())
        self.assertIn("Total execution time", buffer.getvalue())
