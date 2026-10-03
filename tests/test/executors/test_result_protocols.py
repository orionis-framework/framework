import unittest
from orionis.test import TestCase
from orionis.test.enums.status import TestStatus
from orionis.test.executors.results import TestResultProcessor

def _probe_subtests(case: unittest.TestCase) -> None:
    """Emit passing, failing and errored subtests.

    Parameters
    ----------
    case : unittest.TestCase
        Test instance that records each parameterized outcome.
    """
    for value in (0, 1, 2):
        with case.subTest(value=value):
            if value == 1:
                case.fail("Subtest assertion failed.")
            if value == 2:
                message = "Subtest raised an exception."
                raise RuntimeError(message)

def _probe_success(_case: unittest.TestCase) -> None:
    """Complete a test marked as an expected failure.

    Parameters
    ----------
    _case : unittest.TestCase
        Test instance whose body succeeds.
    """

class TestResultProtocols(TestCase):

    def testSubtestFailuresReachExportedResults(self) -> None:
        """Export each failed subtest with its parent source metadata."""
        probe_type = type(
            "ProbeSubtests", (unittest.TestCase,), {"testProbe": _probe_subtests},
        )
        processor = TestResultProcessor(verbosity=0)
        probe_type("testProbe").run(processor)
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

    def testSubtestFailureHonorsFailFast(self) -> None:
        """Stop after the first failed subtest when fail-fast is enabled."""
        probe_type = type(
            "ProbeSubtests", (unittest.TestCase,), {"testProbe": _probe_subtests},
        )
        processor = TestResultProcessor(verbosity=0)
        processor.failfast = True
        probe_type("testProbe").run(processor)
        self.assertTrue(processor.shouldStop)
        self.assertEqual(len(processor.getTestResults()), 1)

    def testExpectedFailureIsReportedAsSkipped(self) -> None:
        """Keep expected failures visible without failing the suite."""
        probe_type = type(
            "ProbeExpectedFailure", (unittest.TestCase,), {
                "testProbe": _probe_subtests,
                "__unittest_expecting_failure__": True,
            },
        )
        processor = TestResultProcessor(verbosity=0)
        probe_type("testProbe").run(processor)
        self.assertEqual(len(processor.expectedFailures), 1)
        self.assertEqual(processor.getTestResults()[0].status, TestStatus.SKIPPED)
        self.assertTrue(processor.wasSuccessful())

    def testUnexpectedSuccessIsReportedAsFailure(self) -> None:
        """Fail exported results when an expected failure unexpectedly passes."""
        probe_type = type(
            "ProbeUnexpectedSuccess", (unittest.TestCase,), {
                "testProbe": _probe_success,
                "__unittest_expecting_failure__": True,
            },
        )
        processor = TestResultProcessor(verbosity=0)
        probe_type("testProbe").run(processor)
        self.assertEqual(len(processor.unexpectedSuccesses), 1)
        self.assertEqual(processor.getTestResults()[0].status, TestStatus.FAILED)
        self.assertFalse(processor.wasSuccessful())
