from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.queue.enums.drivers import Drivers
from orionis.foundation.config.validation import (
    validate_driver, validate_name, validate_seconds,
)
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True, slots=True)
class Sync(BaseEntity):
    """
    Configure the synchronous queue connection.

    Parameters
    ----------
    driver : Drivers | str
        Synchronous driver identifier.
    queue : str
        Default logical queue name read from ``QUEUE_SYNC_QUEUE``.
    retry_after : float
        Reservation duration read from ``QUEUE_SYNC_RETRY_AFTER`` in seconds.
    """

    driver: Drivers | str = Drivers.SYNC

    queue: str = field(
        default_factory=lambda: Env.get("QUEUE_SYNC_QUEUE", "default"),
        metadata={
            "description": "Default sync queue name.",
            "default": "default",
        },
    )

    retry_after: float = field(
        default_factory=lambda: Env.get("QUEUE_SYNC_RETRY_AFTER", 90.0),
        metadata={
            "description": "Sync reservation duration.",
            "default": 90.0,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the driver, queue name, and reservation duration.

        Returns
        -------
        None
            Keep validated connection settings unchanged.

        Raises
        ------
        TypeError
            If a setting has an invalid type.
        ValueError
            If the driver, identifier, or duration is invalid.
        """
        super().__post_init__()
        validate_driver(self.driver, Drivers.SYNC)
        validate_name(self.queue, "connection queue")
        validate_seconds(self.retry_after, "retry_after", positive=True)
