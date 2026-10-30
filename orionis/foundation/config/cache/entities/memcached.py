from __future__ import annotations
from dataclasses import dataclass, field
from typing import Self
from orionis.environment import Env
from orionis.foundation.config.validation import validate_store_port
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Memcached(BaseEntity):
    """
    Represent the configuration entity for a Memcached cache store.

    Attributes
    ----------
    driver : str
        The driver type. Defaults to ``'memcached'``.
    endpoint : str | None
        Memcached host address. Resolved from the ``MEMCACHED_HOST``
        environment variable or defaults to ``'127.0.0.1'``.
    port : int
        Memcached port number. Resolved from the ``MEMCACHED_PORT``
        environment variable or defaults to ``11211``.
    """

    driver: str = field(
        default="memcached",
        metadata={
            "description": (
                "The driver type for the cache store. Defaults to 'memcached'."
            ),
            "default": "memcached",
        },
    )

    endpoint: str | None = field(
        default_factory=lambda: Env.get("MEMCACHED_HOST", "127.0.0.1"),
        metadata={
            "description": "Memcached host address.",
            "default": "127.0.0.1",
        },
    )

    port: int = field(
        default_factory=lambda: Env.get("MEMCACHED_PORT", 11211),
        metadata={
            "description": "Memcached port.",
            "default": 11211,
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
        if self.driver != "memcached":
            error_msg = "The 'driver' property must be 'memcached'."
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

    def __post_init__(self: Self) -> None:
        """
        Validate the Memcached configuration after initialization.

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
