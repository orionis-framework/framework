from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.queue.enums.drivers import Drivers
from orionis.foundation.config.validation import (
    validate_driver,
    validate_integer,
    validate_name,
    validate_seconds,
    validate_string,
)
from orionis.support.entities.base import BaseEntity

_MAX_PORT = 65535

@dataclass(frozen=True, kw_only=True, slots=True)
class Redis(BaseEntity):
    """
    Configure a durable Redis queue connection.

    Parameters
    ----------
    driver : Drivers | str
        Redis driver identifier.
    endpoint : str
        Redis host read from ``REDIS_HOST``.
    port : int
        TCP port read from ``REDIS_PORT``, between 1 and 65535.
    db : int
        Nonnegative database index read from ``REDIS_DB``.
    password : str | None
        Optional authentication password read from ``REDIS_PASSWORD``.
    prefix : str
        Namespace read from ``QUEUE_REDIS_PREFIX`` to isolate persisted jobs.
    queue : str
        Default logical queue name read from ``QUEUE_REDIS_QUEUE``.
    retry_after : float
        Reservation duration read from ``QUEUE_REDIS_RETRY_AFTER`` in seconds.
    """

    driver: Drivers | str = Drivers.REDIS

    endpoint: str = field(
        default_factory=lambda: Env.get("REDIS_HOST", "127.0.0.1"),
        metadata={
            "description": "Redis host address.",
            "default": "127.0.0.1",
        },
    )
    port: int = field(
        default_factory=lambda: Env.get("REDIS_PORT", 6379),
        metadata={
            "description": "Redis port.",
            "default": 6379,
        },
    )

    db: int = field(
        default_factory=lambda: Env.get("REDIS_DB", 0),
        metadata={
            "description": "Redis database index.",
            "default": 0,
        },
    )
    password: str | None = field(
        default_factory=lambda: Env.get("REDIS_PASSWORD"),
        metadata={
            "description": "Redis password.",
            "default": None,
        },
    )
    prefix: str = field(
        default_factory=lambda: Env.get("QUEUE_REDIS_PREFIX", "orionis:queues"),
        metadata={
            "description": "Redis queue namespace.",
            "default": "orionis:queues",
        },
    )
    queue: str = field(
        default_factory=lambda: Env.get("QUEUE_REDIS_QUEUE", "default"),
        metadata={
            "description": "Default Redis queue name.",
            "default": "default",
        },
    )
    retry_after: float = field(
        default_factory=lambda: Env.get("QUEUE_REDIS_RETRY_AFTER", 90.0),
        metadata={
            "description": "Redis reservation duration.",
            "default": 90.0,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate Redis connection fields, namespace, and reservation duration.

        Returns
        -------
        None
            Keep validated connection settings unchanged.

        Raises
        ------
        TypeError
            If a setting has an invalid type.
        ValueError
            If a driver, identifier, numeric range, or duration is invalid.
        """
        super().__post_init__()
        validate_driver(self.driver, Drivers.REDIS)
        validate_string(self.endpoint, "redis endpoint")
        validate_integer(self.port, "redis port", minimum=1, maximum=_MAX_PORT)
        validate_integer(self.db, "redis db")
        if self.password is not None:
            validate_string(self.password, "redis password", allow_empty=True)
        validate_string(self.prefix, "redis prefix")
        validate_name(self.queue, "connection queue")
        validate_seconds(self.retry_after, "retry_after", positive=True)
