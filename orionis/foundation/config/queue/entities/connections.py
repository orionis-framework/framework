from dataclasses import dataclass, field
from orionis.foundation.config.queue.entities.database import Database
from orionis.foundation.config.queue.entities.redis import Redis
from orionis.foundation.config.queue.entities.sync import Sync
from orionis.support.entities.base import BaseEntity

_CONNECTION_ENTITIES = (("sync", Sync), ("database", Database), ("redis", Redis))

@dataclass(frozen=True, kw_only=True, slots=True)
class Connections(BaseEntity):
    """
    Group the conventional validated queue connections.

    Parameters
    ----------
    sync : Sync | dict
        Synchronous connection settings.
    database : Database | dict
        Durable database connection settings.
    redis : Redis | dict
        Durable Redis connection settings.
    """

    sync: Sync | dict = field(
        default_factory=Sync,
        metadata={
            "description": "Synchronous connection settings.",
            "default_factory": Sync().toDict(),
        },
    )

    database: Database | dict = field(
        default_factory=Database,
        metadata={
            "description": "Durable database connection settings.",
            "default_factory": Database().toDict(),
        },
    )

    redis: Redis | dict = field(
        default_factory=Redis,
        metadata={
            "description": "Durable Redis connection settings.",
            "default_factory": Redis().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """Convert connection mappings into strictly validated entities.

        Returns
        -------
        None
            Store an entity for each supported connection.

        Raises
        ------
        TypeError
            If a connection has an unexpected type or unsupported fields.
        ValueError
            If a nested setting fails its connection's validation.
        """
        super().__post_init__()
        for name, entity_type in _CONNECTION_ENTITIES:
            value = getattr(self, name)
            if isinstance(value, dict):
                object.__setattr__(self, name, entity_type(**value))
            elif not isinstance(value, entity_type):
                message = f"'{name}' must be a {entity_type.__name__} or dictionary."
                raise TypeError(message)
