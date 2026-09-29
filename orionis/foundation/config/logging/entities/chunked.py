from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.logging.enums import Level
from orionis.foundation.config.logging.validators import IsValidLevel, IsValidPath
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Chunked(BaseEntity):
    """
    Configure chunked log file rotation.

    This class defines the configuration for managing log files by splitting
    them into chunks based on file size and limiting the number of retained
    log files. This prevents log files from growing indefinitely and helps
    manage disk usage.

    Attributes
    ----------
    path : str
        Filesystem path where chunked log files are stored.
    level : int | str | Level
        Logging level for the log file. Accepts an integer, string, or Level enum.
    mb_size : int
        Maximum size (in megabytes) of a single log file before a new chunk is
        created.
    files : int
        Maximum number of log files to retain. Older files are deleted when this
        limit is exceeded.
    """

    path: str = field(
        default_factory=lambda: Env.get(
            "LOG_PATH",
            "storage/logs/chunked_{suffix}.log",
        ),
        metadata={
            "description": "The file path where the log is stored.",
            "default": "storage/logs/chunked_{suffix}.log",
        },
    )

    level: int | str | Level = field(
        default_factory=lambda: Env.get("LOG_LEVEL", Level.INFO),
        metadata={
            "description": (
                "The logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)."
            ),
            "default": "INFO",
        },
    )

    mb_size: int = field(
        default_factory=lambda: Env.get("LOG_MB_SIZE", 10),
        metadata={
            "description": "Maximum size (in MB) of a log file before chunking.",
            "default": 10,
        },
    )

    files: int = field(
        default_factory=lambda: Env.get("LOG_FILES", 5),
        metadata={
            "description": "Maximum number of log files to retain.",
            "default": 5,
        },
    )

    def __post_init__(self: Chunked) -> None:
        """
        Validate and normalize configuration fields after initialization.

        Validates the following:
        - path: Ensures the path is valid using IsValidPath.
        - level: Ensures the log level is valid using IsValidLevel.
        - mb_size: Checks that it is an integer between 1 and 1000 (MB).
        - files: Checks that it is a positive integer greater than 0.

        Parameters
        ----------
        self : Chunked
            The instance of the Chunked configuration.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If any configuration value is invalid.
        TypeError
            If any configuration value has an incorrect type.
        """
        # Call the superclass post-init method for base validation
        super().__post_init__()

        # Validate 'path' using the IsValidPath validator
        IsValidPath(self.path, suffix=True)

        # Validate 'level' using the IsValidLevel validator
        object.__setattr__(self, "level", IsValidLevel.normalize(self.level))

        # Normalise the level value to integer

        # Validate 'mb_size' type and range
        if not isinstance(self.mb_size, int) or isinstance(self.mb_size, bool):
            error_msg = (
                "'mb_size' must be an integer in MB, got "
                f"{type(self.mb_size).__name__}."
            )
            raise TypeError(error_msg)
        maximum_size = 1000
        if self.mb_size < 1 or self.mb_size > maximum_size:
            error_msg = (
                f"'mb_size' must be between 1 and {maximum_size} MB, got "
                f"{self.mb_size}."
            )
            raise ValueError(error_msg)

        # Validate 'files' type and value
        if not isinstance(self.files, int) or isinstance(self.files, bool):
            error_msg = f"'files' must be an integer, got {type(self.files).__name__}."
            raise TypeError(error_msg)
        if self.files < 1:
            error_msg = (
                f"'files' must be a positive integer greater than 0, got {self.files}."
            )
            raise ValueError(error_msg)
