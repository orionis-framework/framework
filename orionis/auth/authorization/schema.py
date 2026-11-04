"""Build the framework-owned role and permission storage definitions."""

from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, DateTime, String

_PERMISSION_ID_COMMENT: str = "Permission ID"
"""SQL comment shared by permission identifier columns."""
_ROLE_ID_COMMENT: str = "Role ID"
"""SQL comment shared by role identifier columns."""

def build_authorization_tables() -> tuple[TableDefinition, ...]:
    """
    Build role and permission storage in foreign-key dependency order.

    Returns
    -------
    tuple of orionis.orm.schema.TableDefinition
        Fresh definitions for capabilities and their polymorphic assignments.
    """
    tables = (
        TableDefinition(
            name="permissions",
            columns={
                "id": (
                    BigInteger()
                    .primary()
                    .autoIncrement()
                    .comment(_PERMISSION_ID_COMMENT)
                ),
                "name": String(255).unique().comment("Permission Name"),
                "created_at": DateTime().nullable(),
                "updated_at": DateTime().nullable(),
            },
            comment="Table to store permissions.",
        ),
        TableDefinition(
            name="roles",
            columns={
                "id": BigInteger().primary().autoIncrement().comment(_ROLE_ID_COMMENT),
                "name": String(255).unique().comment("Role Name"),
                "created_at": DateTime().nullable(),
                "updated_at": DateTime().nullable(),
            },
            comment="Table to store roles.",
        ),
        TableDefinition(
            name="model_has_permissions",
            columns={
                "permission_id": (
                    BigInteger()
                    .foreign("permissions.id")
                    .comment(_PERMISSION_ID_COMMENT)
                ),
                "model_type": String(255).comment("Model Class Name"),
                "model_id": String(255).comment("Canonical Model ID"),
            },
            composite_primary_key=("permission_id", "model_id", "model_type"),
            indexes=(TableIndex(columns=("model_id", "model_type")),),
            comment="Table to relate permissions with any model (morph).",
        ),
        TableDefinition(
            name="model_has_roles",
            columns={
                "role_id": BigInteger().foreign("roles.id").comment(_ROLE_ID_COMMENT),
                "model_type": String(255).comment("Model Class Name"),
                "model_id": String(255).comment("Canonical Model ID"),
            },
            composite_primary_key=("role_id", "model_id", "model_type"),
            indexes=(TableIndex(columns=("model_id", "model_type")),),
            comment="Table to relate roles with any model (morph).",
        ),
        TableDefinition(
            name="role_has_permissions",
            columns={
                "permission_id": (
                    BigInteger()
                    .foreign("permissions.id")
                    .comment(_PERMISSION_ID_COMMENT)
                ),
                "role_id": BigInteger().foreign("roles.id").comment(_ROLE_ID_COMMENT),
            },
            composite_primary_key=("permission_id", "role_id"),
            indexes=(TableIndex(columns=("role_id", "permission_id")),),
            comment="Table to relate roles with permissions.",
        ),
    )
    for table in tables:
        for name, column in table.columns.items():
            column.name = name
    return tables
