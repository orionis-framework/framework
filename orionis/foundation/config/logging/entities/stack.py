from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.logging.enums import Level
from orionis.foundation.config.logging.validators import IsValidLevel, IsValidPath
from orionis.support.entities.base import BaseEntity

_DEFAULT_PATH: str = "storage/logs/stack.log"

@dataclass(frozen=True, kw_only=True)
class Stack(BaseEntity):
    """
    Represent the configuration for a logging stack.

    Parameters
    ----------
    path : str
        The file path where the log is stored.
    level : int | str | Level
        The logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Attributes
    ----------
    path : str
        The file path where the log is stored.
    level : int | str | Level
        The logging level.
    """

    path: str = field(
        default_factory=lambda: (
            Env.get("LOG_PATH", _DEFAULT_PATH)
            if Env.get("LOG_CHANNEL", "stack") == "stack"
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

    def __post_init__(self) -> None:
        """
        Validate the log path and normalize the configured level.

        Returns
        -------
        None
            Store the validated numeric logging level.

        Raises
        ------
        ValueError
            If the log path is invalid.
        """
        super().__post_init__()
        IsValidPath(self.path)
        object.__setattr__(self, "level", IsValidLevel.normalize(self.level))
