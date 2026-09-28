from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, DateTime, String

ROLES_V1 = TableDefinition(
    name="roles",
    columns={
        "id": BigInteger().primary().autoIncrement().comment("Role ID"),
        "name": String(255).unique().comment("Role Name"),
        "created_at": DateTime().nullable(),
        "updated_at": DateTime().nullable(),
    },
    comment="Table to store roles.",
)
