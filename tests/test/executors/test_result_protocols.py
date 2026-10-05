import asyncio
from orionis.test import TestCase
from orionis.test.enums.status import TestStatus
from orionis.test.executors.results import TestResultProcessor

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

    async def testSubtestFailuresReachExportedResults(self) -> None:
        """Export each failed subtest with its parent source metadata.

        Returns
        -------
        None
            Verify native cases report both assertion and exception failures.
        """
        probe_type = type(
            "ProbeSubtests", (TestCase,), {"testProbe": _probe_subtests},
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
            "ProbeSubtests", (TestCase,), {"testProbe": _probe_subtests},
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
            "ProbeExpectedFailure", (TestCase,), {
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
            "ProbeUnexpectedSuccess", (TestCase,), {
                "testProbe": _probe_success,
                "__unittest_expecting_failure__": True,
            },
        )
        processor = TestResultProcessor(verbosity=0)
        await asyncio.to_thread(probe_type("testProbe").run, processor)
        self.assertEqual(len(processor.unexpectedSuccesses), 1)
        self.assertEqual(processor.getTestResults()[0].status, TestStatus.FAILED)
        self.assertFalse(processor.wasSuccessful())
