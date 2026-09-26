from __future__ import annotations

from dataclasses import dataclass, field

from orionis.foundation.config.queue.entities.database import Database
from orionis.support.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class Brokers(BaseEntity):
    """
    Represent the configuration for queue brokers.

    Parameters
    ----------
    database : Database | dict, optional
        The configuration for the database-backed queue. Defaults to a new
        Database instance.

    Returns
    -------
    None
        This class does not return a value.
    """

    database: Database | dict = field(
        default_factory=Database,
        metadata={
            "description": "The configuration for the database-backed queue.",
            "default": lambda: Database().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize properties after initialization.

        Parameters
        ----------
        self : Brokers
            The Brokers instance being initialized.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Call the superclass post-initialization
        super().__post_init__()

        # Ensure 'database' is a Database instance or dict, convert if needed
        if not isinstance(self.database, (Database, dict)):
            error_msg = (
                "database must be an instance of the Database class or a dictionary."
            )
            raise TypeError(error_msg)
        if isinstance(self.database, dict):
            object.__setattr__(self, "database", Database(**self.database))
