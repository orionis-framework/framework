from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_integer, validate_string
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True, slots=True)
class Redis(BaseEntity):
    """
    Configure the Redis connection used by HTTP rate limiting.

    Attributes
    ----------
    endpoint : str
        Redis host address, read from ``REDIS_HOST``.
    port : int
        Redis TCP port, read from ``REDIS_PORT``.
    db : int
        Redis database index, read from ``REDIS_DB``.
    password : str | None
        Optional Redis password, read from ``REDIS_PASSWORD``.
    """

    endpoint: str = field(
        default_factory=lambda: Env.get("REDIS_HOST", "127.0.0.1"),
        metadata={"description": "Redis host address.", "default": "127.0.0.1"},
    )

    port: int = field(
        default_factory=lambda: Env.get("REDIS_PORT", 6379),
        metadata={"description": "Redis port.", "default": 6379},
    )

    db: int = field(
        default_factory=lambda: Env.get("REDIS_DB", 0),
        metadata={"description": "Redis database index.", "default": 0},
    )

    password: str | None = field(
        default_factory=lambda: Env.get("REDIS_PASSWORD", None),
        metadata={"description": "Redis password.", "default": None},
    )

    def __post_init__(self) -> None:
        """
        Validate connection fields without creating a Redis client.

        Returns
        -------
        None
            Reject invalid connection settings during configuration loading.

        Raises
        ------
        TypeError
            If a field has an unexpected type.
        ValueError
            If the endpoint is empty, the port is invalid or the db is negative.
        """
        BaseEntity.__post_init__(self)
        validate_string(self.endpoint, "endpoint")
        validate_integer(self.port, "port", minimum=1, maximum=65535)
        validate_integer(self.db, "db")
        if self.password is not None:
            validate_string(self.password, "password", allow_empty=True)
