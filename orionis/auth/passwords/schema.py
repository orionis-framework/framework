"""Build the framework-owned password-reset token storage definition."""

from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String

def build_password_reset_table(table: str) -> TableDefinition:
    """
    Build the schema consumed by the password-reset broker.

    Parameters
    ----------
    table : str
        Logical reset table name, before the SQL connection prefix is applied.

    Returns
    -------
    orionis.orm.schema.TableDefinition
        One reset credential per email, with hashed secrets and UTC Unix seconds.
    """
    columns = {
        "email": String(255).primary(),
        "token": String(64).nullable(),
        "user_id": String(255),
        "password_fingerprint": String(64),
        "created_at": BigInteger().index(),
    }
    for name, column in columns.items():
        column.name = name
    return TableDefinition(
        name=table,
        columns=columns,
        primary_key="email",
        indexes=(TableIndex(columns=("token",)),),
        comment="Store for password reset tokens, one per email.",
    )
