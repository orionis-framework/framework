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

    def __post_init__(self) -> None:
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
        self.__validateTable()
