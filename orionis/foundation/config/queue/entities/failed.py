from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_name
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True, slots=True)
class Failed(BaseEntity):
    """
    Configure database storage for failed jobs.

    Parameters
    ----------
    connection : str | None
        Framework database connection, or its default when omitted.
    table : str
        Unqualified SQL table used to preserve failed jobs.
    """

    connection: str | None = field(
        default_factory=lambda: Env.get("QUEUE_FAILED_DB_CONNECTION"),
    )
    table: str = field(
        default_factory=lambda: Env.get("QUEUE_FAILED_TABLE", "failed_jobs"),
    )

    def __post_init__(self) -> None:
        """Validate the failed-job database connection and table.

        Returns
        -------
        None
            Keep validated failure storage settings unchanged.

        Raises
        ------
        TypeError
            If an identifier has an invalid type.
        ValueError
            If an identifier is empty or unsafe.
        """
        super().__post_init__()
        if self.connection is not None:
            validate_name(self.connection, "failed connection")
        validate_name(self.table, "failed table", table=True)
