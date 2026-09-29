from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_string
from orionis.support.entities.base import BaseEntity

# Highest valid TCP/UDP port number.
_MAX_PORT = 65535

@dataclass(frozen=True, kw_only=True)
class Redis(BaseEntity):
    """
    Represent the configuration entity for a Redis job store.

    Attributes
    ----------
    driver : str
        The driver type. Defaults to ``'redis'``.
    host : str
        Redis host address. Defaults to ``'localhost'``.
    port : int
        Redis port number. Defaults to ``6379``.
    db : int
        Redis database index. Defaults to ``0``.
    key : str
        Redis key used to store the serialized job definitions. Defaults
        to ``'scheduler:tasks'``.
    run_times_key : str
        Redis key used to store the next-run-time index for scheduled
        jobs. Defaults to ``'scheduler:run_times'``.
    """

    driver: str = field(
        default="redis",
        metadata={
            "description": ("The driver type for the job store. Defaults to 'redis'."),
            "default": "redis",
        },
    )

    host: str = field(
        default_factory=lambda: Env.get("REDIS_HOST", "localhost"),
        metadata={
            "description": "Redis host address.",
            "default": "localhost",
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
        default_factory=lambda: Env.get("REDIS_PASSWORD", None),
        metadata={
            "description": "Redis password for authentication.",
            "default": None,
        },
    )

    key: str = field(
        default_factory=lambda: Env.get("REDIS_TASKS_KEY", "scheduler:tasks"),
        metadata={
            "description": ("Redis key used to store the serialized job definitions."),
            "default": "scheduler:tasks",
        },
    )

    run_times_key: str = field(
        default_factory=lambda: Env.get("REDIS_RUN_TIMES_KEY", "scheduler:run_times"),
        metadata={
            "description": (
                "Redis key used to store the next-run-time index for scheduled jobs."
            ),
            "default": "scheduler:run_times",
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
        # Ensure the driver is set to 'redis' for this store.
        if self.driver != "redis":
            message = f"Invalid driver for Redis store: {self.driver}"
            raise ValueError(message)

    def __validateHost(self) -> None:
        """
        Validate the ``host`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``host`` is not a string.
        ValueError
            If ``host`` is an empty string.
        """
        if not isinstance(self.host, str):
            error_msg = "The 'host' property must be a string."
            raise TypeError(error_msg)
        if not self.host.strip():
            error_msg = "The 'host' property cannot be empty."
            raise ValueError(error_msg)

    def __validatePort(self) -> None:
        """
        Validate the ``port`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``port`` is not an integer.
        ValueError
            If ``port`` is not between ``1`` and ``65535``.
        """
        if not isinstance(self.port, int) or isinstance(self.port, bool):
            error_msg = "The 'port' property must be an integer."
            raise TypeError(error_msg)
        if not (1 <= self.port <= _MAX_PORT):
            error_msg = f"The 'port' property must be between 1 and {_MAX_PORT}."
            raise ValueError(error_msg)

    def __validateDb(self) -> None:
        """
        Validate the ``db`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``db`` is not an integer.
        ValueError
            If ``db`` is negative.
        """
        if not isinstance(self.db, int) or isinstance(self.db, bool):
            error_msg = "The 'db' property must be an integer."
            raise TypeError(error_msg)
        if self.db < 0:
            error_msg = "The 'db' property cannot be negative."
            raise ValueError(error_msg)

    def __validateKey(self) -> None:
        """
        Validate the ``key`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``key`` is not a string.
        ValueError
            If ``key`` is an empty string.
        """
        if not isinstance(self.key, str):
            error_msg = "The 'key' property must be a string."
            raise TypeError(error_msg)
        if not self.key.strip():
            error_msg = "The 'key' property cannot be empty."
            raise ValueError(error_msg)

    def __validateRunTimesKey(self) -> None:
        """
        Validate the ``run_times_key`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``run_times_key`` is not a string.
        ValueError
            If ``run_times_key`` is an empty string.
        """
        if not isinstance(self.run_times_key, str):
            error_msg = "The 'run_times_key' property must be a string."
            raise TypeError(error_msg)
        if not self.run_times_key.strip():
            error_msg = "The 'run_times_key' property cannot be empty."
            raise ValueError(error_msg)

    def __post_init__(self) -> None:
        """
        Validate the Redis job store configuration after initialization.

        Returns
        -------
        None
            Validates every field against its declared type hint.

        Raises
        ------
        TypeError
            If any property does not match its expected type.
        ValueError
            If any property fails its value validation.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Validate each property according to its type hint
        self.__validateDriver()
        self.__validateHost()
        self.__validatePort()
        self.__validateDb()
        self.__validateKey()
        self.__validateRunTimesKey()

        if self.password is not None:
            validate_string(self.password, "password", allow_empty=True)
        if self.key == self.run_times_key:
            message = "Redis job and run time keys must be different."
            raise ValueError(message)
