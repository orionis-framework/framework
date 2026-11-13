# ruff: noqa: PLR2004, PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import asyncio
import unittest
from orionis.test import TestCase
from orionis.test.enums.status import TestStatus
from orionis.test.executors.results import TestResultProcessor
from orionis.test.executors.runner import TestRunner


def _probe_subtests(case: TestCase) -> None:
    """Emit passing, failing and errored subtests.

    Parameters
    ----------
    case : TestCase
        Test instance that records each parameterized outcome.

    Returns
    -------
    None
        Record the successful, failed and errored subtest outcomes.
    """
    for value in (0, 1, 2):
        with case.subTest(value=value):
            if value == 1:
                case.fail("Subtest assertion failed.")
            if value == 2:
                message = "Subtest raised an exception."
                raise RuntimeError(message)


def _probe_success(_case: TestCase) -> None:
    """Complete a test marked as an expected failure.

    Parameters
    ----------
    _case : TestCase
        Test instance whose body succeeds.

    Returns
    -------
    None
        Finish without producing the expected failure.
    """


class TestResultProtocols(TestCase):
    async def testClassFixtureFailuresAreReportedBeforeAnyTestStarts(self) -> None:
        """Preserve setup errors and skips reported before the first test."""
        for error in (
            ValueError("fixture failed"),
            unittest.SkipTest("fixture skipped"),
        ):
            with self.subTest(error=type(error).__name__):

                def set_up_class(
                    _cls: type,
                    error: Exception = error,
                ) -> None:
                    """Raise the selected fixture outcome before test execution.

                    Parameters
                    ----------
                    _cls : type
                        Generated case class supplied by unittest.
                    error : Exception
                        Error or skip selected by the current scenario.

                    Raises
                    ------
                    Exception
                        Always raise the selected fixture outcome.
                    """
                    raise error

                probe_type = type(
                    "ProbeClassFixture",
                    (unittest.TestCase,),
                    {
                        "setUpClass": classmethod(set_up_class),
                        "testProbe": _probe_success,
                    },
                )
                suite = unittest.TestLoader().loadTestsFromTestCase(probe_type)
                result = await asyncio.to_thread(
                    TestRunner(with_panel=False).run,
                    suite,
                )
                reports = result.getTestResults()
                self.assertEqual(len(reports), 1)
                expected = (
                    TestStatus.SKIPPED
                    if isinstance(error, unittest.SkipTest)
                    else TestStatus.ERRORED
                )
                self.assertEqual(reports[0].status, expected)
                self.assertEqual(result.testsRun, 0)
                self.assertEqual(reports[0].execution_time, 0.0)
                self.assertEqual(result.wasSuccessful(), expected == TestStatus.SKIPPED)

    async def testSubtestFailuresReachExportedResults(self) -> None:
        """Export each failed subtest with its parent source metadata.

        Returns
        -------
        None
            Verify native cases report both assertion and exception failures.
        """
        probe_type = type(
            "ProbeSubtests",
            (TestCase,),
            {"testProbe": _probe_subtests},
        )
        processor = TestResultProcessor(verbosity=0)
        await asyncio.to_thread(probe_type("testProbe").run, processor)
        results = processor.getTestResults()
        self.assertEqual(
            [result.status for result in results],
            [TestStatus.FAILED, TestStatus.ERRORED],
        )
        self.assertEqual(len(processor.failures), 1)
        self.assertEqual(len(processor.errors), 1)
        self.assertEqual(processor.testsRun, 1)
        self.assertIn("value=1", results[0].name)
        self.assertIn("value=2", results[1].name)
        self.assertEqual(results[0].class_name, "ProbeSubtests")
        self.assertEqual(results[0].method, "testProbe")
        self.assertFalse(processor.wasSuccessful())

    async def testSubtestFailureHonorsFailFast(self) -> None:
        """Stop after the first failed subtest when fail-fast is enabled.

        Returns
        -------
        None
            Verify a native case stops at its first failed subtest.
        """
        probe_type = type(
            "ProbeSubtests",
            (TestCase,),
            {"testProbe": _probe_subtests},
        )
        processor = TestResultProcessor(verbosity=0)
        processor.failfast = True
        await asyncio.to_thread(probe_type("testProbe").run, processor)
        self.assertTrue(processor.shouldStop)
        self.assertEqual(len(processor.getTestResults()), 1)

    async def testExpectedFailureIsReportedAsSkipped(self) -> None:
        """Keep expected failures visible without failing the suite.

        Returns
        -------
        None
            Verify a native case records expected failures as skipped results.
        """
        probe_type = type(
            "ProbeExpectedFailure",
            (TestCase,),
            {
                "testProbe": _probe_subtests,
                "__unittest_expecting_failure__": True,
            },
        )
        processor = TestResultProcessor(verbosity=0)
        await asyncio.to_thread(probe_type("testProbe").run, processor)
        self.assertEqual(len(processor.expectedFailures), 1)
        self.assertEqual(processor.getTestResults()[0].status, TestStatus.SKIPPED)
        self.assertTrue(processor.wasSuccessful())

    async def testUnexpectedSuccessIsReportedAsFailure(self) -> None:
        """Fail exported results when an expected failure unexpectedly passes.

        Returns
        -------
        None
            Verify a native case preserves unexpected-success failure status.
        """
        probe_type = type(
            "ProbeUnexpectedSuccess",
            (TestCase,),
            {
                "testProbe": _probe_success,
                "__unittest_expecting_failure__": True,
            },
        )
        processor = TestResultProcessor(verbosity=0)
        await asyncio.to_thread(probe_type("testProbe").run, processor)
        self.assertEqual(len(processor.unexpectedSuccesses), 1)
        self.assertEqual(processor.getTestResults()[0].status, TestStatus.FAILED)
        self.assertFalse(processor.wasSuccessful())
