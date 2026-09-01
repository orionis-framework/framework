from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Highest valid TCP/UDP port number.
_MAX_PORT = 65535

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
                "The driver type for the cache store. "
                "Defaults to 'memcached'."
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

    def __post_init__(self) -> None:
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
        self.__validatePort()
