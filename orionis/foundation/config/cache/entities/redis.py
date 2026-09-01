from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Highest valid TCP/UDP port number.
_MAX_PORT = 65535

@dataclass(frozen=True, kw_only=True)
class Redis(BaseEntity):
    """
    Represent the configuration entity for a Redis cache store.

    Attributes
    ----------
    driver : str
        The driver type. Defaults to ``'redis'``.
    endpoint : str | None
        Redis host address. Resolved from the ``REDIS_HOST`` environment
        variable or defaults to ``'127.0.0.1'``.
    port : int
        Redis port number. Resolved from the ``REDIS_PORT`` environment
        variable or defaults to ``6379``.
    db : int
        Redis database index. Resolved from the ``REDIS_DB`` environment
        variable or defaults to ``0``.
    password : str | None
        Redis password. Resolved from the ``REDIS_PASSWORD`` environment
        variable or defaults to ``None``.
    """

    driver: str = field(
        default="redis",
        metadata={
            "description": (
                "The driver type for the cache store. Defaults to 'redis'."
            ),
            "default": "redis",
        },
    )

    endpoint: str | None = field(
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

    def __validateEndpoint(self) -> None:
        """
        Validate the ``endpoint`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``endpoint`` is neither a string nor ``None``.
        """
        if self.endpoint is not None and not isinstance(self.endpoint, str):
            error_msg = "The 'endpoint' property must be a string or None."
            raise TypeError(error_msg)

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
            error_msg = (
                f"The 'port' property must be between 1 and {_MAX_PORT}."
            )
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

    def __validatePassword(self) -> None:
        """
        Validate the ``password`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``password`` is neither a string nor ``None``.
        """
        if self.password is not None and not isinstance(self.password, str):
            error_msg = "The 'password' property must be a string or None."
            raise TypeError(error_msg)

    def __post_init__(self) -> None:
        """
        Validate the Redis configuration after initialization.

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
        self.__validateEndpoint()
        self.__validatePort()
        self.__validateDb()
        self.__validatePassword()
