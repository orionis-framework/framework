from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String, Text

SESSIONS_V1 = TableDefinition(
    name="sessions",
    columns={
        "id": String(255).primary().comment("Session ID"),
        "payload": Text().comment("Session Payload"),
        "expires_at": BigInteger().comment("Expiration"),
    },
    comment="Table to store session records.",
)
