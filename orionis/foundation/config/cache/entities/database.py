from __future__ import annotations
import re
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Table names must start and contain only lowercase letters or underscores.
_TABLE_NAME_PATTERN = re.compile(r"[a-z_]+")

@dataclass(frozen=True, kw_only=True)
class Database(BaseEntity):
    """
    Represent the configuration entity for a database-backed cache store.

    Mirrors ``database`` cache store configuration array,
    supporting a dedicated connection/table for cache entries and an
    independent connection/table for the atomic locks used by
    ``Cache::lock()``.

    Attributes
    ----------
    driver : str
        The driver type. Defaults to ``'database'``.
    connection : str | None
        The database connection name used to store cache entries.
        Resolved from the ``DB_CACHE_CONNECTION`` environment variable or
        ``None`` to use the application's default connection.
    table : str
        The database table name used to store cache entries. Must match
        the pattern ``[a-z_]+``. Resolved from the ``DB_CACHE_TABLE``
        environment variable or defaults to ``'cache'``.
    lock_table : str | None
        The database table name used to store cache locks. Must match
        the pattern ``[a-z_]+`` when provided. Resolved from the
        ``DB_CACHE_LOCK_TABLE`` environment variable or ``None`` to let
        the driver fall back to its own default.
    """

    driver: str = field(
        default="database",
        metadata={
            "description": (
                "The driver type for the cache store. Defaults to 'database'."
            ),
            "default": "database",
        },
    )

    connection: str | None = field(
        default_factory=lambda: Env.get("DB_CACHE_CONNECTION"),
        metadata={
            "description": (
                "The database connection name used to store cache entries. "
                "Defaults to the 'DB_CACHE_CONNECTION' environment variable "
                "or None to use the application's default connection."
            ),
            "default": None,
        },
    )

    table: str = field(
        default_factory=lambda: Env.get("DB_CACHE_TABLE", "cache"),
        metadata={
            "description": (
                "The database table name used to store cache entries. "
                "Defaults to the 'DB_CACHE_TABLE' environment variable "
                "or 'cache'."
            ),
            "default": "cache",
        },
    )

    lock_table: str | None = field(
        default_factory=lambda: Env.get("DB_CACHE_LOCK_TABLE"),
        metadata={
            "description": (
                "The database table name used to store cache locks. "
                "Defaults to the 'DB_CACHE_LOCK_TABLE' environment "
                "variable or None."
            ),
            "default": None,
        },
    )

    def __validateDriver(self) -> None:
        """
        Validate the ``driver`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``driver`` is not a string.
        ValueError
            If ``driver`` is an empty string.
        """
        # Check type before truthiness to avoid misleading error messages
        if not isinstance(self.driver, str):
            error_msg = "The 'driver' property must be a string."
            raise TypeError(error_msg)
        if not self.driver:
            error_msg = "The 'driver' property cannot be empty."
            raise ValueError(error_msg)

    def __validateConnection(self) -> None:
        """
        Validate the ``connection`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``connection`` is neither a string nor ``None``.
        """
        if self.connection is not None and not isinstance(self.connection, str):
            error_msg = "The 'connection' property must be a string or None."
            raise TypeError(error_msg)

    def __validateTable(self) -> None:
        """
        Validate the ``table`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``table`` is not a string.
        ValueError
            If ``table`` does not match the required pattern.
        """
        if not isinstance(self.table, str):
            error_msg = "The 'table' property must be a string."
            raise TypeError(error_msg)
        if not _TABLE_NAME_PATTERN.fullmatch(self.table):
            error_msg = (
                "The 'table' property must be a valid table name: contain "
                "only lowercase letters or underscores (no numbers allowed)."
            )
            raise ValueError(error_msg)

    def __validateLockTable(self) -> None:
        """
        Validate the ``lock_table`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``lock_table`` is neither a string nor ``None``.
        ValueError
            If ``lock_table`` is provided but does not match the required
            pattern.
        """
        if self.lock_table is None:
            return
        if not isinstance(self.lock_table, str):
            error_msg = "The 'lock_table' property must be a string or None."
            raise TypeError(error_msg)
        if not _TABLE_NAME_PATTERN.fullmatch(self.lock_table):
            error_msg = (
                "The 'lock_table' property must be a valid table name: "
                "contain only lowercase letters or underscores (no numbers "
                "allowed)."
            )
            raise ValueError(error_msg)

    def __post_init__(self) -> None:
        """
        Validate the Database cache configuration after initialization.

        Returns
        -------
        None
            Validates every field against its declared type hint.

        Raises
        ------
        TypeError
            If any property does not match its expected type.
        ValueError
            If ``table`` or ``lock_table`` fail table-name validation.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Validate each property according to its type hint
        self.__validateDriver()
        self.__validateConnection()
        self.__validateTable()
        self.__validateLockTable()
