from orionis.orm.schema.constraints import TableIndex
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String

PASSWORD_RESET_TOKENS_V1 = TableDefinition(
    name="password_reset_tokens",
    columns={
        "email": String(255).primary(),
        "token": String(64).nullable(),
        "user_id": String(255),
        "password_fingerprint": String(64),
        "created_at": BigInteger().index(),
    },
    primary_key="email",
    indexes=(
        TableIndex(
            columns=(
                "token",
            ),
        ),
    ),
    comment="Store for password reset tokens, one per email.",
)
