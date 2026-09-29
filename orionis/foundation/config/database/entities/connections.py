from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.database.entities.mysql import MySQL
from orionis.foundation.config.database.entities.oracle import Oracle
from orionis.foundation.config.database.entities.pgsql import PGSQL
from orionis.foundation.config.database.entities.sqlite import SQLite
from orionis.foundation.config.database.entities.sqlserver import SQLServer
from orionis.support.entities.base import BaseEntity

# Table-driven mapping between connection field names and their entities.
_CONNECTION_ENTITIES: tuple[tuple[str, type], ...] = (
    ("sqlite", SQLite),
    ("mysql", MySQL),
    ("pgsql", PGSQL),
    ("oracle", Oracle),
    ("sqlserver", SQLServer),
)

@dataclass(frozen=True, kw_only=True)
class Connections(BaseEntity):
    """
    Represent all database connections used by the application.

    Attributes
    ----------
    sqlite : SQLite | dict
        Configuration for the SQLite database connection.
    mysql : MySQL | dict
        Configuration for the MySQL database connection.
    pgsql : PGSQL | dict
        Configuration for the PostgreSQL database connection.
    oracle : Oracle | dict
        Configuration for the Oracle database connection.
    sqlserver : SQLServer | dict
        Configuration for the Microsoft SQL Server database connection.
    """

    sqlite: SQLite | dict = field(
        default_factory=SQLite,
        metadata={
            "description": "SQLite database connection configuration",
            "default": lambda: SQLite().toDict(),
        },
    )

    mysql: MySQL | dict = field(
        default_factory=MySQL,
        metadata={
            "description": "MySQL database connection configuration",
            "default": lambda: MySQL().toDict(),
        },
    )

    pgsql: PGSQL | dict = field(
        default_factory=PGSQL,
        metadata={
            "description": "PostgreSQL database connection configuration",
            "default": lambda: PGSQL().toDict(),
        },
    )

    oracle: Oracle | dict = field(
        default_factory=Oracle,
        metadata={
            "description": "Oracle database connection configuration",
            "default": lambda: Oracle().toDict(),
        },
    )

    sqlserver: SQLServer | dict = field(
        default_factory=SQLServer,
        metadata={
            "description": "SQL Server database connection configuration",
            "default": lambda: SQLServer().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and convert database connection attributes after initialization.

        Ensures every connection attribute is an instance of its entity
        class, converting from a dictionary when needed.

        Raises
        ------
        TypeError
            If any attribute is not an instance of its expected class or dict.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__post_init__()

        # Validate and convert each connection entry uniformly.
        for name, entity_cls in _CONNECTION_ENTITIES:
            value = getattr(self, name)
            if not isinstance(value, (entity_cls, dict)):
                error_msg = (
                    f"Invalid type for '{name}': expected "
                    f"'{entity_cls.__name__}' or 'dict', got "
                    f"'{type(value).__name__}'."
                )
                raise TypeError(error_msg)
            if isinstance(value, dict):
                # Convert dict payloads into their validated entity.
                object.__setattr__(self, name, entity_cls(**value))
