from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.logging.enums import Level
from orionis.foundation.config.logging.validators import IsValidLevel, IsValidPath
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Monthly(BaseEntity):
    """
    Represent the configuration for monthly log file management.

    Attributes
    ----------
    path : str
        The file path where the log is stored.
    level : int | str | Level
        The logging level (e.g., 'info', 'error', 'debug').
    retention_months : int
        The number of months to retain log files before deletion.
    """

    path: str = field(
        default_factory=lambda: Env.get(
            "LOG_PATH",
            "storage/logs/monthly_{suffix}.log",
        ),
        metadata={
            "description": "The file path where the log is stored.",
            "default": "storage/logs/monthly_{suffix}.log",
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

    retention_months: int = field(
        default_factory=lambda: Env.get("LOG_RETENTION", 4),
        metadata={
            "description": (
                "The number of months to retain log files before deletion."
            ),
            "default": 4,
        },
    )

    def __post_init__(self: Monthly) -> None:
        """
        Validate and normalize attributes after dataclass initialization.

        Parameters
        ----------
        self : Monthly
            Instance of the Monthly configuration entity.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If any attribute is invalid.
        TypeError
            If any attribute has an incorrect type.
        KeyError
            If the logging level is not a valid Level enum name.
        """
        # Call the superclass's __post_init__ method.
        super().__post_init__()

        # Validate 'path' using the IsValidPath validator.
        IsValidPath(self.path, suffix=True)

        # Validate 'level' using the IsValidLevel validator.
        object.__setattr__(self, "level", IsValidLevel.normalize(self.level))

        # Validate 'retention_months' is an integer between 1 and 12.
        if not isinstance(self.retention_months, int) or isinstance(
            self.retention_months,
            bool,
        ):
            error_msg = (
                f"Invalid type for 'retention_months': expected int, got "
                f"{type(self.retention_months).__name__}."
            )
            raise TypeError(error_msg)
        maximum_retention = 12
        if not (1 <= self.retention_months <= maximum_retention):
            error_msg = (
                f"'retention_months' must be an integer between 1 and "
                f"{maximum_retention} (inclusive), got {self.retention_months}."
            )
            raise ValueError(error_msg)
