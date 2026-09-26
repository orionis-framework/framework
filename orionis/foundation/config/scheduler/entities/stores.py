from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.scheduler.entities.database import Database
from orionis.foundation.config.scheduler.entities.memory import Memory
from orionis.foundation.config.scheduler.entities.redis import Redis
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Stores(BaseEntity):
    """
    Represent a collection of scheduler job store backends.

    Attributes
    ----------
    memory : Memory | dict | None
        In-memory job store configuration. Defaults to ``None``.
    redis : Redis | dict | None
        Redis job store configuration. Defaults to ``None``.
    database : Database | dict | None
        Database-backed job store configuration. Defaults to ``None``.
    """

    memory: Memory | dict | None = field(
        default_factory=Memory,
        metadata={
            "description": "In-memory job store configuration.",
            "default": lambda: Memory().toDict(),
        },
    )

    redis: Redis | dict | None = field(
        default_factory=Redis,
        metadata={
            "description": "Redis job store configuration.",
            "default": lambda: Redis().toDict(),
        },
    )

    database: Database | dict | None = field(
        default_factory=Database,
        metadata={
            "description": "Database-backed job store configuration.",
            "default": lambda: Database().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and convert store configuration attributes after init.

        Returns
        -------
        None
            Validates all store fields and converts dicts to typed instances.

        Raises
        ------
        TypeError
            If any store attribute is not of the expected type.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Validate each store field in declaration order
        self.__validateOptional("memory", Memory)
        self.__validateOptional("redis", Redis)
        self.__validateOptional("database", Database)

    def __validateOptional(self, name: str, cls: type) -> None:
        """
        Validate and optionally convert an optional store attribute.

        Parameters
        ----------
        name : str
            Name of the attribute to validate on this instance.
        cls : type
            Expected concrete type for the attribute value.

        Returns
        -------
        None
            Converts a ``dict`` value to a ``cls`` instance via
            ``object.__setattr__`` when applicable.

        Raises
        ------
        TypeError
            If the attribute value is not an instance of ``cls``, a
            ``dict``, or ``None``.
        """
        # Retrieve the current attribute value by name
        value = getattr(self, name)

        # None signals that the optional store is disabled; skip validation
        if value is None:
            return

        # Reject unexpected types before attempting conversion
        if not isinstance(value, (cls, dict)):
            error_msg = (
                f"The '{name}' attribute must be an instance of "
                f"{cls.__name__}, a dict, or None, but got "
                f"{type(value).__name__}."
            )
            raise TypeError(error_msg)

        # Convert dict representation to the target typed instance
        if isinstance(value, dict):
            object.__setattr__(self, name, cls(**value))
