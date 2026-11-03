"""Represent possible statuses for a test during execution."""

from enum import StrEnum

class TestStatus(StrEnum):
    """
    Represent possible statuses for a test during execution.

    Attributes
    ----------
    PASSED : orionis.test.enums.status.TestStatus
        Indicates the test completed successfully without errors or failures.
    FAILED : orionis.test.enums.status.TestStatus
        Indicates the test completed but did not produce the expected results.
    ERRORED : orionis.test.enums.status.TestStatus
        Indicates an unexpected error occurred during test execution.
    SKIPPED : orionis.test.enums.status.TestStatus
        Indicates the test was intentionally not executed.

    Returns
    -------
    orionis.test.enums.status.TestStatus
        Enumeration member representing the test status.
    """

    PASSED = "PASSED"
    FAILED = "FAILED"
    ERRORED = "ERRORED"
    SKIPPED = "SKIPPED"
