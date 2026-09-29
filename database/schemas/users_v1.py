from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, Boolean, DateTime, String

USERS_V1 = TableDefinition(
    name="users",
    columns={
        "id": BigInteger().primary().autoIncrement().comment("User ID"),
        "name": String(255).comment("Full Name"),
        "email": String(255).unique().comment("Email Address"),
        "email_verified_at": DateTime().nullable().comment("Email Verification Timestamp"),
        "password": String(255).comment("Hashed Password"),
        "remember_token": String(100).nullable().comment("Expiring Remember Me Token Digest"),
        "active": Boolean().default(value=True).comment("Active Status"),
        "created_at": DateTime().nullable(),
        "updated_at": DateTime().nullable(),
    },
    comment="Table to store application users.",
)
