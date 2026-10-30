from __future__ import annotations
from dataclasses import dataclass, field
from typing import Self
from orionis.environment import Env
from orionis.foundation.config.validation import validate_store_table
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Database(BaseEntity):
    """
    Represent the configuration entity for a database-backed job store.

    Mirrors APScheduler's SQLAlchemy job store configuration, allowing a
    dedicated connection/table to persist scheduled task definitions.

    Attributes
    ----------
    driver : str
        The driver type. Defaults to ``'database'``.
    connection : str | None
        The database connection name used to store scheduled tasks.
        Resolved from the ``DB_TASK_CONNECTION`` environment variable or
        ``None`` to use the application's default connection.
    table : str
        The database table name used to store scheduled tasks. Must match
        the pattern ``[a-z_]+``. Resolved from the ``DB_TASK_TABLE``
        environment variable or defaults to ``'scheduler_tasks'``.
    """

    driver: str = field(
        default="database",
        metadata={
            "description": (
                "The driver type for the job store. Defaults to 'database'."
            ),
            "default": "database",
        },
    )

    connection: str | None = field(
        default_factory=lambda: Env.get("DB_TASK_CONNECTION"),
        metadata={
            "description": (
                "The database connection name used to store scheduled "
                "tasks. Defaults to the 'DB_TASK_CONNECTION' environment "
                "variable or None to use the application's default "
                "connection."
            ),
            "default": None,
        },
    )

    table: str = field(
        default_factory=lambda: Env.get("DB_TASK_TABLE", "scheduler_tasks"),
        metadata={
            "description": (
                "The database table name used to store scheduled tasks. "
                "Defaults to the 'DB_TASK_TABLE' environment variable or "
                "'scheduler_tasks'."
            ),
            "default": "scheduler_tasks",
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
        # Ensure the driver is set to 'database' for this store.
        if self.driver != "database":
            error_msg = f"Invalid driver for Database store: {self.driver}"
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
        Validate the Database job store configuration after initialization.

        Returns
        -------
        None
            Validates every field against its declared type hint.

        Raises
        ------
        TypeError
            If any property does not match its expected type.
        ValueError
            If ``table`` fails table-name validation.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Validate each property according to its type hint
        self.__validateDriver()
        self.__validateConnection()
        validate_store_table(self.table)
