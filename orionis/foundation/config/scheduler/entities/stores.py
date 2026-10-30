from __future__ import annotations
from dataclasses import dataclass, field
from typing import Self
from orionis.foundation.config.scheduler.entities.database import Database
from orionis.foundation.config.scheduler.entities.memory import Memory
from orionis.foundation.config.scheduler.entities.redis import Redis
from orionis.foundation.config.validation import normalize_optional_store
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

    def __post_init__(self: Self) -> None:
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
        normalize_optional_store(self, "memory", Memory)
        normalize_optional_store(self, "redis", Redis)
        normalize_optional_store(self, "database", Database)
