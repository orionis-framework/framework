from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.logging.enums import Level
from orionis.foundation.config.logging.validators import IsValidLevel, IsValidPath
from orionis.support.entities.base import BaseEntity

_DEFAULT_PATH: str = "storage/logs/hourly_{suffix}.log"

@dataclass(frozen=True, kw_only=True)
class Hourly(BaseEntity):
    """
    Represent the configuration for hourly log file management.

    Parameters
    ----------
    path : str
        The file path where the log is stored.
    level : int | str | Level
        The logging level (e.g., 'info', 'error', 'debug').
    retention_hours : int
        The number of hours to retain log files before deletion.

    Returns
    -------
    None
        This class does not return a value.
    """

    path: str = field(
        default_factory=lambda: (
            Env.get("LOG_PATH", _DEFAULT_PATH)
            if Env.get("LOG_CHANNEL", "stack") == "hourly"
            else _DEFAULT_PATH
        ),
        metadata={
            "description": "The file path where the log is stored.",
            "default": _DEFAULT_PATH,
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

    retention_hours: int = field(
        default_factory=lambda: (
            Env.get("LOG_RETENTION", 24)
            if Env.get("LOG_CHANNEL", "stack") == "hourly" else 24
        ),
        metadata={
            "description": ("The number of hours to retain log files before deletion."),
            "default": 24,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate attributes after dataclass initialization.

        Parameters
        ----------
        self : Hourly
            The instance of the Hourly class.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If 'retention_hours' is not a non-negative integer.
        ValueError
            If 'retention_hours' is not between 1 and 168.
        """
        # Call the parent class's __post_init__ method.
        super().__post_init__()

        # Validate 'path' using the IsValidPath validator.
        IsValidPath(self.path, suffix=True)

        # Validate 'level' using the IsValidLevel validator.
        object.__setattr__(self, "level", IsValidLevel.normalize(self.level))

        # Normalise the logging level to its integer value.

        # Ensure 'retention_hours' is a non-negative integer.
        if (
            not isinstance(self.retention_hours, int)
            or isinstance(self.retention_hours, bool)
            or self.retention_hours < 0
        ):
            error_msg = (
                "File cache configuration error: 'retention_hours' must be a "
                f"non-negative integer, got {self.retention_hours}."
            )
            raise TypeError(error_msg)
        # Ensure 'retention_hours' is within the valid range.
        max_retention = 168
        if self.retention_hours < 1 or self.retention_hours > max_retention:
            error_msg = (
                "File cache configuration error: 'retention_hours' must be "
                f"between 1 and {max_retention}, got {self.retention_hours}."
            )
            raise ValueError(error_msg)
