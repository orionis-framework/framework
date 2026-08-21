from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from orionis.support.entities.base import BaseEntity

if TYPE_CHECKING:
    from orionis.test.enums.status import TestStatus

@dataclass(frozen=True, kw_only=True)
class TestResult(BaseEntity):
    """
    Represent the outcome of a test execution.

    Parameters
    ----------
    id : Any
        Unique identifier for the test result.
    name : str
        Name of the test.
    status : TestStatus
        Status of the test execution (e.g., passed, failed).
    execution_time : float
        Time taken to execute the test, in seconds.
    error_message : str | None, optional
        Error message if the test failed, otherwise None.
    traceback : list[str] | None, optional
        Formatted traceback lines if an error occurred, otherwise None.
    class_name : str | None, optional
        Name of the class containing the test, if applicable.
    method : str | None, optional
        Name of the method representing the test, if applicable.
    module : str | None, optional
        Name of the module containing the test, if applicable.
    file_path : str | None, optional
        Path to the file containing the test, if applicable.
    doc_string : str | None, optional
        Docstring of the test, if applicable.
    exception : str | None, optional
        Name of the raised exception class if an error occurred, otherwise None.
    line_no : int | None, optional
        Line number in the source file where the test is defined, if applicable.

    Returns
    -------
    None
        This class does not return a value upon instantiation.
    """

    # Unique identifier for the test result
    id: Any = field(
        metadata={
            "description": "Unique identifier for the test result.",
        },
    )

    # Name of the test
    name: str = field(
        metadata={
            "description": "Name of the test.",
        },
    )

    # Status of the test execution (e.g., passed, failed)
    status: TestStatus = field(
        metadata={
            "description": (
                "Status of the test execution (e.g., passed, failed)."
            ),
        },
    )

    # Time taken to execute the test, in seconds
    execution_time: float = field(
        metadata={
            "description": (
                "Time taken to execute the test, in seconds."
            ),
        },
    )

    # Error message if the test failed, otherwise None
    error_message: str | None = field(
        default=None,
        metadata={
            "description": (
                "Error message if the test failed, otherwise None."
            ),
        },
    )

    # Traceback information if an error occurred, otherwise None
    traceback: list[str] | None = field(
        default=None,
        metadata={
            "description": (
                "Formatted traceback lines if an error occurred, otherwise None."
            ),
        },
    )

    # Name of the class containing the test, if applicable
    class_name: str | None = field(
        default=None,
        metadata={
            "description": (
                "Name of the class containing the test, if applicable."
            ),
        },
    )

    # Name of the method representing the test, if applicable
    method: str | None = field(
        default=None,
        metadata={
            "description": (
                "Name of the method representing the test, if applicable."
            ),
        },
    )

    # Name of the module containing the test, if applicable
    module: str | None = field(
        default=None,
        metadata={
            "description": (
                "Name of the module containing the test, if applicable."
            ),
        },
    )

    # Path to the file containing the test, if applicable
    file_path: str | None = field(
        default=None,
        metadata={
            "description": (
                "Path to the file containing the test, if applicable."
            ),
        },
    )

    # Docstring of the test, if applicable
    doc_string: str | None = field(
        default=None,
        metadata={
            "description": (
                "Docstring of the test, if applicable."
            ),
        },
    )

    # The exception class name if an error occurred, otherwise None
    exception: str | None = field(
        default=None,
        metadata={
            "description": (
                "Name of the raised exception class if an error occurred, "
                "otherwise None."
            ),
        },
    )

    # Line number in the source file where the test is defined, if applicable
    line_no: int | None = field(
        default=None,
        metadata={
            "description": (
                "Line number in the source file where the test is defined, "
                "if applicable."
            ),
        },
    )

    source_code: list[tuple[int, str]] | None = field(
        default=None,
        metadata={
            "description": (
                "Source code lines surrounding the error, as (line_no, code) "
                "pairs, if an error occurred, otherwise None."
            ),
        },
    )
