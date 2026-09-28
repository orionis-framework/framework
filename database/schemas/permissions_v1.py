from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, DateTime, String

PERMISSIONS_V1 = TableDefinition(
    name="permissions",
    columns={
        "id": BigInteger().primary().autoIncrement().comment("Permission ID"),
        "name": String(255).unique().comment("Permission Name"),
        "created_at": DateTime().nullable(),
        "updated_at": DateTime().nullable(),
    },
    comment="Table to store permissions.",
)
