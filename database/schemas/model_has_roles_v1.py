from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String

MODEL_HAS_ROLES_V1 = TableDefinition(
    name="model_has_roles",
    columns={
        "role_id": BigInteger().foreign("roles.id").comment("Role ID"),
        "model_type": String(255).comment("Model Class Name"),
        "model_id": String(255).comment("Canonical Model ID"),
    },
    composite_primary_key=("role_id", "model_id", "model_type"),
    indexes=(
        TableIndex(
            columns=(
                "model_id",
                "model_type",
            ),
        ),
    ),
    comment="Table to relate roles with any model (morph).",
)
