import re
from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Double, Integer, LargeBinary, String, Text
from orionis.queues.exceptions import QueueConfigurationError

_TABLE_NAME = re.compile(r"[A-Za-z_]\w*", re.ASCII)

def validate_table_name(table: str) -> str:
    """
    Validate a logical table identifier.

    Parameters
    ----------
    table : str
        Logical table name without the database connection prefix.

    Returns
    -------
    str
        Validated table identifier.

    Raises
    ------
    QueueConfigurationError
        If the table identifier is invalid.
    """
    if not isinstance(table, str) or _TABLE_NAME.fullmatch(table) is None:
        message = "Queue table names must be valid SQL identifiers."
        raise QueueConfigurationError(message)
    return table

def build_jobs_table(table: str) -> TableDefinition:
    """
    Build the portable queue storage schema.

    Parameters
    ----------
    table : str
        Logical table name for durable queued jobs.

    Returns
    -------
    TableDefinition
        Queue schema with lease fencing and fractional epoch timestamps.
    """
    return TableDefinition(
        name=validate_table_name(table),
        columns={
            "id": String(36).primary(),
            "queue": String(255),
            "payload": LargeBinary(),
            "attempts": Integer(),
            "available_at": Double(),
            "reserved_until": Double().nullable(),
            "reservation_token": String(32).nullable(),
            "created_at": Double(),
        },
        primary_key="id",
        indexes=(
            TableIndex(columns=("queue", "available_at", "reserved_until")),
        ),
    )

def build_failed_jobs_table(table: str) -> TableDefinition:
    """
    Build the portable failed-job storage schema.

    Parameters
    ----------
    table : str
        Logical table name for failed jobs.

    Returns
    -------
    TableDefinition
        Failure schema retaining the original envelope and exception details.
    """
    return TableDefinition(
        name=validate_table_name(table),
        columns={
            "id": String(36).primary(),
            "job_id": String(36),
            "connection": String(255),
            "queue": String(255),
            "payload": LargeBinary(),
            "attempts": Integer(),
            "exception_type": String(255),
            "exception_message": Text(),
            "traceback": Text(),
            "failed_at": Double(),
        },
        primary_key="id",
        indexes=(TableIndex(columns=("failed_at",)),),
    )
