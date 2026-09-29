from enum import StrEnum

class TestStatus(StrEnum):
    """
    Represent possible statuses for a test during execution.

    Attributes
    ----------
    PASSED : TestStatus
        Indicates the test completed successfully without errors or failures.
    FAILED : TestStatus
        Indicates the test completed but did not produce the expected results.
    ERRORED : TestStatus
        Indicates an unexpected error occurred during test execution.
    SKIPPED : TestStatus
        Indicates the test was intentionally not executed.

    Returns
    -------
    TestStatus
        Enumeration member representing the test status.
    """

    PASSED = "PASSED"
    FAILED = "FAILED"
    ERRORED = "ERRORED"
    SKIPPED = "SKIPPED"
