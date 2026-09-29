from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.database.enums import (
    SQLiteForeignKey,
    SQLiteJournalMode,
    SQLiteSynchronous,
)
from orionis.foundation.config.validation import normalize_enum, validate_integer
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class SQLite(BaseEntity):
    """
    Represent the SQLite database configuration.

    Attributes
    ----------
    driver : str
        The database driver being used, e.g., 'sqlite'.
    url : str | None
        Informational URL, derived from database when omitted.
    database : str
        The path to the SQLite database file.
    prefix : str
        Prefix for table names.
    foreign_key_constraints : bool | str | SQLiteForeignKey
        Whether foreign key constraints are enabled.
    busy_timeout : int | None
        The timeout period (in milliseconds) before retrying a locked database.
    journal_mode : str
        The journal mode used for transactions.
    synchronous : str
        The synchronization level for the database.
    """

    driver: str = field(
        default="sqlite",
        metadata={
            "description": "The database driver being used.",
            "example": "sqlite",
        },
    )

    url: str | None = field(
        default_factory=lambda: Env.get("DB_URL"),
        metadata={
            "description": "The URL for connecting to the database.",
            "example": "sqlite:///database/database.sqlite",
        },
    )

    database: str = field(
        default_factory=lambda: Env.get("DB_DATABASE", "database/database.sqlite"),
        metadata={
            "description": "The path to the SQLite database file.",
            "example": "database.sqlite",
        },
    )

    prefix: str = field(
        default_factory=lambda: Env.get("DB_PREFIX", ""),
        metadata={
            "description": "Prefix for table names.",
            "example": "",
        },
    )

    foreign_key_constraints: bool | str | SQLiteForeignKey = field(
        default_factory=lambda: Env.get(
            "DB_FOREIGN_KEYS",
            SQLiteForeignKey.OFF.value,
        ),
        metadata={
            "description": "Whether foreign key constraints are enabled.",
            "example": "OFF",
        },
    )

    busy_timeout: int | None = field(
        default_factory=lambda: Env.get("DB_BUSY_TIMEOUT", 5000),
        metadata={
            "description": (
                "The timeout period (in milliseconds) before retrying a locked "
                "database."
            ),
            "example": 5000,
        },
    )

    journal_mode: str | SQLiteJournalMode = field(
        default_factory=lambda: Env.get(
            "DB_JOURNAL_MODE",
            SQLiteJournalMode.DELETE.value,
        ),
        metadata={
            "description": "The journal mode used for transactions.",
            "example": "DELETE",
        },
    )

    synchronous: str | SQLiteSynchronous = field(
        default_factory=lambda: Env.get(
            "DB_SYNCHRONOUS",
            SQLiteSynchronous.NORMAL.value,
        ),
        metadata={
            "description": "The synchronization level for the database.",
            "example": "NORMAL",
        },
    )

    def __normalizeForeignKeyConstraints(self) -> None:
        """
        Normalize foreign-key settings to SQLite enum values.

        Returns
        -------
        None
            This method updates the frozen entity in place and returns no value.
        """
        # Convert boolean input before applying the enum normalization helper.
        value = self.foreign_key_constraints
        if isinstance(value, bool):
            value = SQLiteForeignKey.ON if value else SQLiteForeignKey.OFF
        object.__setattr__(
            self,
            "foreign_key_constraints",
            normalize_enum(
                value,
                SQLiteForeignKey,
                "foreign_key_constraints",
            ),
        )

    def __normalizeJournalMode(self) -> None:
        """
        Normalize the SQLite journal mode option.

        Returns
        -------
        None
            This method updates the frozen entity in place and returns no value.
        """
        # Store the canonical enum value after validating the configured option.
        object.__setattr__(
            self,
            "journal_mode",
            normalize_enum(
                self.journal_mode,
                SQLiteJournalMode,
                "journal_mode",
            ),
        )

    def __normalizeSynchronous(self) -> None:
        """
        Normalize the SQLite synchronous option.

        Returns
        -------
        None
            This method updates the frozen entity in place and returns no value.
        """
        # Store the canonical enum value after validating the configured option.
        object.__setattr__(
            self,
            "synchronous",
            normalize_enum(
                self.synchronous,
                SQLiteSynchronous,
                "synchronous",
            ),
        )

    def __post_init__(self) -> None:
        """
        Validate SQLite options and derive the informational URL when absent.

        Returns
        -------
        None
            This method validates and normalizes the entity without returning a
            value.

        Raises
        ------
        TypeError
            If a configured option has an invalid type.
        ValueError
            If a configured option has an invalid value.
        """
        super().__post_init__()
        if self.driver != "sqlite":
            error_msg = "The 'driver' property must be 'sqlite'."
            raise ValueError(error_msg)
        if not isinstance(self.database, str) or not self.database.strip():
            error_msg = "'database' must be a non-empty SQLite path or ':memory:'."
            raise ValueError(error_msg)
        if self.url is None:
            object.__setattr__(self, "url", "sqlite:///" + self.database)
        if not isinstance(self.url, str) or not self.url.strip():
            error_msg = "'url' must be a non-empty string or None."
            raise ValueError(error_msg)
        if not isinstance(self.prefix, str):
            error_msg = "'prefix' must be a string."
            raise TypeError(error_msg)
        self.__normalizeForeignKeyConstraints()
        if self.busy_timeout is not None:
            validate_integer(self.busy_timeout, "busy_timeout")
        self.__normalizeJournalMode()
        self.__normalizeSynchronous()
