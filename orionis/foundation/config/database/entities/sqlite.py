from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.database.enums import (
    SQLiteForeignKey,
    SQLiteJournalMode,
    SQLiteSynchronous,
)
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Pre-computed membership
_FK_NAMES: frozenset[str] = frozenset(SQLiteForeignKey._member_names_)
_JOURNAL_NAMES: frozenset[str] = frozenset(SQLiteJournalMode._member_names_)
_SYNC_NAMES: frozenset[str] = frozenset(SQLiteSynchronous._member_names_)

@dataclass(frozen=True, kw_only=True)
class SQLite(BaseEntity):
    """
    Represent the SQLite database configuration.

    Attributes
    ----------
    driver : str
        The database driver being used, e.g., 'sqlite'.
    url : str
        The URL for connecting to the database.
    database : str
        The path to the SQLite database file.
    prefix : str
        Prefix for table names.
    foreign_key_constraints : bool
        Whether foreign key constraints are enabled.
    busy_timeout : int
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

    url: str = field(
        default_factory=lambda: Env.get(
            "DB_URL", "sqlite:///" + Env.get("DB_DATABASE", "database/database.sqlite"),
        ),
        metadata={
            "description": "The URL for connecting to the database.",
            "example": "sqlite:///database/database.sqlite",
        },
    )

    database: str = field(
        default_factory=lambda: Env.get("DB_DATABASE", "database.sqlite"),
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

    foreign_key_constraints: bool | SQLiteForeignKey = field(
        default_factory=lambda: Env.get(
            "DB_FOREIGN_KEYS", SQLiteForeignKey.OFF.value,
        ),
        metadata={
            "description": "Whether foreign key constraints are enabled.",
            "example": SQLiteForeignKey.OFF.value,
        },
    )

    busy_timeout: int = field(
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
            "DB_JOURNAL_MODE", SQLiteJournalMode.DELETE.value,
        ),
        metadata={
            "description": "The journal mode used for transactions.",
            "example": SQLiteJournalMode.DELETE.value,
        },
    )

    synchronous: str | SQLiteSynchronous = field(
        default_factory=lambda: Env.get(
            "DB_SYNCHRONOUS", SQLiteSynchronous.NORMAL.value,
        ),
        metadata={
            "description": "The synchronization level for the database.",
            "example": SQLiteSynchronous.NORMAL.value,
        },
    )

    def __normalizeForeignKeyConstraints(self) -> None:
        """
        Normalize and validate the foreign_key_constraints attribute.

        Converts string values to the corresponding enum value and validates
        that the value is a valid option.

        Parameters
        ----------
        self : SQLite
            The instance of the SQLite configuration entity.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Validate and normalise foreign_key_constraints using pre-cached frozenset
        if isinstance(self.foreign_key_constraints, str):
            _value = self.foreign_key_constraints.upper().strip()
            if _value not in _FK_NAMES:
                error_msg = (
                    "The 'foreign_key_constraints' attribute must be a valid option "
                    f"{sorted(_FK_NAMES)!s}"
                )
                raise ValueError(error_msg)
            object.__setattr__(
                self,
                "foreign_key_constraints",
                SQLiteForeignKey[_value].value,
            )
        else:
            object.__setattr__(
                self,
                "foreign_key_constraints",
                self.foreign_key_constraints.value,
            )

    def __normalizeJournalMode(self) -> None:
        """
        Normalize and validate the journal_mode attribute.

        Converts string values to the corresponding enum value and validates
        that the value is a valid option.

        Parameters
        ----------
        self : SQLite
            The instance of the SQLite configuration entity.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Validate and normalise journal_mode using pre-cached frozenset
        if isinstance(self.journal_mode, str):
            _value = self.journal_mode.upper().strip()
            if _value not in _JOURNAL_NAMES:
                error_msg = (
                    "The 'journal_mode' attribute must be a valid option "
                    f"{sorted(_JOURNAL_NAMES)!s}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "journal_mode", SQLiteJournalMode[_value].value)
        else:
            object.__setattr__(self, "journal_mode", self.journal_mode.value)

    def __normalizeSynchronous(self) -> None:
        """
        Normalize and validate the synchronous attribute.

        Converts string values to the corresponding enum value and validates
        that the value is a valid option.

        Parameters
        ----------
        self : SQLite
            Instance of the SQLite configuration entity.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Validate and normalise synchronous using pre-cached frozenset
        if isinstance(self.synchronous, str):
            _value = self.synchronous.upper().strip()
            if _value not in _SYNC_NAMES:
                error_msg = (
                    "The 'synchronous' attribute must be a valid option "
                    f"{sorted(_SYNC_NAMES)!s}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "synchronous", SQLiteSynchronous[_value].value)
        else:
            object.__setattr__(self, "synchronous", self.synchronous.value)

    def __post_init__(self) -> None:
        """
        Validate and normalize SQLite database configuration fields.

        Validates that all configuration attributes are of the correct type and
        meet required constraints. Converts string values to enum values where
        appropriate.

        Parameters
        ----------
        self : SQLite
            The instance of the SQLite configuration entity.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Call parent post-init for base validation
        super().__post_init__()

        # Validate driver
        if not isinstance(self.driver, str) or not self.driver.strip():
            error_msg = (
                "Invalid 'driver': must be a non-empty string (e.g., 'sqlite')."
            )
            raise ValueError(error_msg)

        # Validate url
        if not isinstance(self.url, str) or not self.url.strip():
            error_msg = (
                "Invalid 'url': must be a non-empty string "
                "(e.g., 'sqlite:///database/database.sqlite')."
            )
            raise ValueError(error_msg)

        # Validate database
        if not isinstance(self.database, str) or not self.database.strip():
            error_msg = (
                "Invalid 'database': must be a non-empty string representing the "
                "database file path."
            )
            raise ValueError(error_msg)

        # Validate prefix
        if not isinstance(self.prefix, str):
            error_msg = "Invalid 'prefix': must be a string (can be empty)."
            raise TypeError(error_msg)

        # Validate and normalize foreign_key_constraints
        self.__normalizeForeignKeyConstraints()

        # Validate busy_timeout
        if (
            self.busy_timeout is not None
            and (not isinstance(self.busy_timeout, int) or self.busy_timeout < 0)
        ):
            error_msg = (
                "Invalid 'busy_timeout': must be a non-negative integer "
                "(milliseconds) or None."
            )
            raise ValueError(error_msg)

        # Validate journal_mode and normalize to enum value
        self.__normalizeJournalMode()

        # Validate synchronous and normalize to enum value
        self.__normalizeSynchronous()
