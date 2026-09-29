from __future__ import annotations

import re
from dataclasses import dataclass, field

from orionis.foundation.config.queue.enums import Strategy
from orionis.foundation.config.validation import (
    normalize_enum,
    validate_integer,
    validate_string,
)
from orionis.support.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class Database(BaseEntity):
    """
    Represent the configuration entity for a database-backed queue.

    Attributes
    ----------
    driver : str
        The driver type for the queue. Defaults to 'database'.
    jobs_table : str
        The name of the table used for the queue. Must match the pattern
        `[a-z_]+` (lowercase letters or underscores only, no numbers).
    failed_jobs_table : str
        The name of the table used for failed jobs. Must match the pattern
        `[a-z_]+` (lowercase letters or underscores only, no numbers).
    queue : str
        The name of the queue. Must contain only ASCII characters.
    visibility_timeout : int
        The time in seconds that a job is hidden from other workers after being
        fetched. Must be a positive integer.
    retry_delay : int
        The time in seconds to wait before retrying a failed job. Must be a
        positive integer.
    max_attempts : int
        The maximum number of attempts for a job before it fails permanently.
        Must be a positive integer.
    strategy : str | Strategy
        The strategy used for the queue. Options are FIFO, LIFO, or PRIORITY.
        Can be provided as a string (case-insensitive) or as a `Strategy` enum
        member.
    """

    driver: str = field(
        default="database",
        metadata={
            "description": "The driver type for the queue. Defaults to 'database'.",
            "default": "database",
        },
    )

    jobs_table: str = field(
        default="jobs",
        metadata={
            "description": "The name of the table used for the queue.",
            "default": "jobs",
        },
    )

    failed_jobs_table: str = field(
        default="failed_jobs",
        metadata={
            "description": "The name of the table used for failed jobs.",
            "default": "failed_jobs",
        },
    )

    queue: str = field(
        default="default",
        metadata={
            "description": "The name of the queue.",
            "default": "default",
        },
    )

    visibility_timeout: int = field(
        default=60,
        metadata={
            "description": (
                "The time in seconds that a job is hidden from other workers "
                "after being fetched."
            ),
            "default": 60,
        },
    )

    retry_delay: int = field(
        default=90,
        metadata={
            "description": (
                "The time in seconds to wait before retrying a failed job."
            ),
            "default": 90,
        },
    )

    max_attempts: int = field(
        default=3,
        metadata={
            "description": (
                "The maximum number of attempts for a job before it fails permanently."
            ),
            "default": 3,
        },
    )

    strategy: str | Strategy = field(
        default=Strategy.FIFO.value,
        metadata={
            "description": (
                "The strategy used for the queue. Options are FIFO, LIFO, or PRIORITY."
            ),
            "default": Strategy.FIFO.value,
        },
    )

    def __validateJobTable(self) -> None:
        """
        Validate the 'jobs_table' property.

        Parameters
        ----------
        self : Database
            The instance of the Database entity.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If 'jobs_table' is not a string.
        ValueError
            If 'jobs_table' does not match the required pattern.
        """
        # Ensure jobs_table is a string and matches the required pattern
        if not isinstance(self.jobs_table, str):
            error_msg = "The 'jobs_table' property must be a string."
            raise TypeError(error_msg)
        if not re.fullmatch(r"[a-z_]+", self.jobs_table):
            error_msg = (
                "The 'jobs_table' property must be a valid table name: start "
                "with a lowercase letter or underscore, contain only lowercase "
                "letters or underscores (no numbers allowed)."
            )
            raise ValueError(error_msg)

    def __validateFailedJobTable(self) -> None:
        """
        Validate the 'failed_jobs_table' property.

        Parameters
        ----------
        self : Database
            The instance of the Database entity.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If 'failed_jobs_table' is not a string.
        ValueError
            If 'failed_jobs_table' does not match the required pattern.
        """
        # Ensure failed_jobs_table is a string and matches the required pattern
        if not isinstance(self.failed_jobs_table, str):
            error_msg = "The 'failed_jobs_table' property must be a string."
            raise TypeError(error_msg)
        if not re.fullmatch(r"[a-z_]+", self.failed_jobs_table):
            error_msg = (
                "The 'failed_jobs_table' property must be a valid table name: "
                "start with a lowercase letter or underscore, contain only "
                "lowercase letters or underscores (no numbers allowed)."
            )
            raise ValueError(error_msg)

    def __post_init__(self) -> None:
        """Validate queue storage, retry limits, and ordering strategy."""
        super().__post_init__()
        if self.driver != "database":
            message = "The 'driver' property must be 'database'."
            raise ValueError(message)
        self.__validateJobTable()
        self.__validateFailedJobTable()
        validate_string(self.queue, "queue")
        if not self.queue.isascii():
            message = "The 'queue' property must contain only ASCII characters."
            raise ValueError(message)
        for name in ("visibility_timeout", "retry_delay", "max_attempts"):
            validate_integer(getattr(self, name), name, minimum=1)
        object.__setattr__(
            self,
            "strategy",
            normalize_enum(
                self.strategy,
                Strategy,
                "strategy",
            ),
        )
