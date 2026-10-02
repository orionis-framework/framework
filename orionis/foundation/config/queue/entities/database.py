from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.queue.enums.drivers import Drivers
from orionis.foundation.config.validation import (
    validate_driver, validate_name, validate_seconds,
)
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True, slots=True)
class Database(BaseEntity):
    """
    Configure a durable database queue connection.

    Parameters
    ----------
    driver : Drivers | str
        Database driver identifier.
    connection : str | None
        Framework database connection, or its default when omitted.
    table : str
        Unqualified SQL table used to persist jobs.
    queue : str
        Default logical queue name read from ``QUEUE_DB_QUEUE``.
    retry_after : float
        Reservation duration read from ``QUEUE_DB_RETRY_AFTER`` in seconds.
    """

    driver: Drivers | str = Drivers.DATABASE

    connection: str | None = field(
        default_factory=lambda: Env.get("QUEUE_DB_CONNECTION"),
        metadata={
            "description": "Framework database connection.",
            "default": None,
        },
    )

    table: str = field(
        default_factory=lambda: Env.get("QUEUE_TABLE", "jobs"),
        metadata={
            "description": "Unqualified SQL table used to persist jobs.",
            "default": "jobs",
        },
    )

    queue: str = field(
        default_factory=lambda: Env.get("QUEUE_DB_QUEUE", "default"),
        metadata={
            "description": "Default database queue name.",
            "default": "default",
        },
    )

    retry_after: float = field(
        default_factory=lambda: Env.get("QUEUE_DB_RETRY_AFTER", 90.0),
        metadata={
            "description": "Database reservation duration.",
            "default": 90.0,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the driver, database identifiers, and reservation duration.

        Returns
        -------
        None
            Keep validated connection settings unchanged.

        Raises
        ------
        TypeError
            If a setting has an invalid type.
        ValueError
            If a driver, identifier, or duration is invalid.
        """
        super().__post_init__()
        validate_driver(self.driver, Drivers.DATABASE)
        if self.connection is not None:
            validate_name(self.connection, "database connection")
        validate_name(self.table, "database table", table=True)
        validate_name(self.queue, "connection queue")
        validate_seconds(self.retry_after, "retry_after", positive=True)
