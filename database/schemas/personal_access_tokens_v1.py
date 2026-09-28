from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, DateTime, String, Text

PERSONAL_ACCESS_TOKENS_V1 = TableDefinition(
    name="personal_access_tokens",
    columns={
        "id": BigInteger().primary().autoIncrement().comment("Token ID"),
        "tokenable_type": String(255).comment("Owner Class Name"),
        "tokenable_id": String(255).comment("Canonical Owner ID"),
        "name": String(255).comment("Token Label"),
        "token": String(64).unique().comment("SHA-256 Digest"),
        "abilities": Text().nullable().comment("Granted Abilities"),
        "last_used_at": DateTime().nullable().comment("Last Used At"),
        "expires_at": DateTime().nullable().index().comment("Expires At"),
        "revoked_at": DateTime().nullable().index().comment("Revoked At"),
        "created_at": DateTime().nullable(),
        "updated_at": DateTime().nullable(),
    },
    indexes=(
        TableIndex(
            columns=(
                "tokenable_type",
                "tokenable_id",
            ),
        ),
    ),
    comment="Table to store personal access tokens.",
)
