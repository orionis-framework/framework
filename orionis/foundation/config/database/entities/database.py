from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.database.entities.connections import Connections
from orionis.foundation.config.database.enums.connection_name import ConnectionName
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Pre-computed frozenset of valid connection names for O(1) membership checks
_CONNECTION_NAMES: frozenset[str] = frozenset(ConnectionName._member_names_)

@dataclass(frozen=True, kw_only=True)
class Database(BaseEntity):
    """
    Represent the general database configuration.

    Attributes
    ----------
    default : ConnectionName | str
        The name of the default database connection to use. Accepts a
        ``ConnectionName`` enum member or a plain string (e.g. ``'sqlite'``).
    connections : Connections or dict
        The different database connections available to the application.
    """

    default: ConnectionName | str = field(
        default_factory=lambda: Env.get("DB_CONNECTION", ConnectionName.SQLITE.value),
        metadata={
            "description": (
                "The default database connection name. Can be a member of the "
                "ConnectionName enum or a string (e.g., 'sqlite', 'mysql')."
            ),
            "default": ConnectionName.SQLITE.value,
        },
    )

    connections: Connections | dict = field(
        default_factory=Connections,
        metadata={
            "description": "Database connections",
            "default": lambda: Connections().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize the 'default' and 'connections' attributes.

        Validates that the 'default' attribute is a valid ConnectionName member
        or a string corresponding to one. Ensures that the 'connections' attribute
        is an instance of Connections or a non-empty dictionary. Raises an
        exception if validation fails.

        Parameters
        ----------
        self : Database
            The instance of the Database class.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__post_init__()

        # Reject types that are neither ConnectionName enum nor string
        if not isinstance(self.default, (ConnectionName, str)):
            error_msg = (
                "The 'default' attribute must be an instance of "
                "ConnectionName or a string."
            )
            raise TypeError(error_msg)

        # Validate string connection names and normalise to canonical enum value
        if isinstance(self.default, str):
            _value = self.default.upper().strip()
            if _value not in _CONNECTION_NAMES:
                error_msg = (
                    "The 'default' attribute must be one of "
                    f"{sorted(m.value for m in ConnectionName)!s}."
                )
                raise ValueError(error_msg)
            # Normalise to the canonical string value stored in the enum
            object.__setattr__(self, "default", ConnectionName[_value].value)
        else:
            # Extract the raw string value from the ConnectionName enum member
            object.__setattr__(self, "default", self.default.value)

        # Validate the 'connections' attribute
        if not self.connections or not isinstance(
            self.connections, (Connections, dict),
        ):
            error_msg = (
                "The 'connections' attribute must be an instance of Connections or a "
                "non-empty dictionary."
            )
            raise TypeError(error_msg)
        # Convert dict to Connections if necessary
        if isinstance(self.connections, dict):
            object.__setattr__(self, "connections", Connections(**self.connections))
