from __future__ import annotations
from dataclasses import dataclass, field
from typing import Self
from orionis.environment import Env
from orionis.foundation.config.validation import validate_store_table
from orionis.support.entities.base import BaseEntity

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
        default_factory=lambda: Env.get("DB_CACHE_LOCK_TABLE", "cache_locks"),
        metadata={
            "description": (
                "The database table name used to store cache locks. "
                "Defaults to the 'DB_CACHE_LOCK_TABLE' environment "
                "variable or None."
            ),
            "default": "cache_locks",
        },
    )

    def __validateDriver(self: Self) -> None:
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
        if self.driver != "database":
            error_msg = "The 'driver' property must be 'database'."
            raise ValueError(error_msg)

    def __validateConnection(self: Self) -> None:
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

    def __post_init__(self: Self) -> None:
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
        validate_store_table(self.table)
        validate_store_table(self.lock_table, "lock_table", optional=True)
