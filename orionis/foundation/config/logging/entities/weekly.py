from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.logging.enums import Level
from orionis.foundation.config.logging.validators import IsValidLevel, IsValidPath
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Weekly(BaseEntity):
    """
    Represent the configuration for weekly log file management.

    Attributes
    ----------
    path : str
        The file path where the log is stored.
    level : int | str | Level
        The logging level (e.g., 'info', 'error', 'debug').
    retention_weeks : int
        The number of weeks to retain log files before deletion.
    """

    path: str = field(
        default_factory=lambda: Env.get("LOG_PATH", "storage/logs/weekly_{suffix}.log"),
        metadata={
            "description": "The file path where the log is stored.",
            "default": "storage/logs/weekly_{suffix}.log",
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

    retention_weeks: int = field(
        default_factory=lambda: Env.get("LOG_RETENTION", 4),
        metadata={
            "description": ("The number of weeks to retain log files before deletion."),
            "default": 4,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize the Weekly configuration after initialization.

        Parameters
        ----------
        self : Weekly
            The instance of the Weekly configuration.

        Returns
        -------
        None
            This method does not return a value.

        Notes
        -----
        Ensures that the path, level, and retention_weeks attributes are valid and
        normalized.
        """
        # Call the parent class's __post_init__ method to ensure base validation.
        super().__post_init__()

        # Validate 'path' using the IsValidPath validator.
        IsValidPath(self.path, suffix=True)

        # Validate 'level' using the IsValidLevel validator.
        object.__setattr__(self, "level", IsValidLevel.normalize(self.level))

        # Normalise the 'level' attribute to its integer value.

        # Validate 'retention_weeks' type.
        if not isinstance(self.retention_weeks, int) or isinstance(
            self.retention_weeks,
            bool,
        ):
            error_msg = (
                "Invalid type for 'retention_weeks': expected int, got "
                f"{type(self.retention_weeks).__name__}."
            )
            raise TypeError(error_msg)
        # Ensure 'retention_weeks' is within the allowed range.
        maximum_weeks = 12
        if self.retention_weeks < 1 or self.retention_weeks > maximum_weeks:
            error_msg = (
                f"'retention_weeks' must be an integer between 1 and "
                f"{maximum_weeks} (inclusive), but got {self.retention_weeks}."
            )
            raise ValueError(error_msg)
