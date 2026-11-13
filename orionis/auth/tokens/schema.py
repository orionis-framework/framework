"""Provide auth tokens operations through ``build_tokens_table``."""

from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, DateTime, String, Text


def build_tokens_table(table: str) -> TableDefinition:
    """
    Build the framework schema consumed by the personal access token repository.

    Parameters
    ----------
    table : str
        Logical token table name, before the SQL connection prefix is applied.

    Returns
    -------
    orionis.orm.schema.TableDefinition
        Token storage with a unique digest, indexed owner, and UTC timestamps.
    """
    columns = {
        "id": BigInteger().primary().autoIncrement(),
        "tokenable_type": String(255),
        "tokenable_id": String(255),
        "name": String(255),
        "token": String(64).unique(),
        "abilities": Text().nullable(),
        "last_used_at": DateTime(timezone=True).nullable(),
        "expires_at": DateTime(timezone=True).nullable(),
        "revoked_at": DateTime(timezone=True).nullable(),
        "created_at": DateTime(timezone=True).nullable(),
        "updated_at": DateTime(timezone=True).nullable(),
    }
    for name, column in columns.items():
        column.name = name
    return TableDefinition(
        name=table,
        columns=columns,
        primary_key="id",
        indexes=(TableIndex(columns=("tokenable_type", "tokenable_id")),),
    )
