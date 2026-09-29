from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger

ROLE_HAS_PERMISSIONS_V1 = TableDefinition(
    name="role_has_permissions",
    columns={
        "permission_id": BigInteger().foreign("permissions.id").comment("Permission ID"),
        "role_id": BigInteger().foreign("roles.id").comment("Role ID"),
    },
    composite_primary_key=("permission_id", "role_id"),
    indexes=(
        TableIndex(
            columns=(
                "role_id",
                "permission_id",
            ),
        ),
    ),
    comment="Table to relate roles with permissions.",
)
