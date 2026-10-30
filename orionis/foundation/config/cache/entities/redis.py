from __future__ import annotations
from dataclasses import dataclass, field
from typing import Self
from orionis.environment import Env
from orionis.foundation.config.validation import validate_store_db, validate_store_port
from orionis.support.entities.base import BaseEntity

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
        # Check type before truthiness to avoid misleading error messages
        if self.driver != "redis":
            error_msg = "The 'driver' property must be 'redis'."
            raise ValueError(error_msg)

    def __validateEndpoint(self: Self) -> None:
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

    def __validatePassword(self: Self) -> None:
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

    def __post_init__(self: Self) -> None:
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
        validate_store_port(self.port)
        validate_store_db(self.db)
        self.__validatePassword()
