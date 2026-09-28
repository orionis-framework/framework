from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Double, String

CACHE_LOCKS_V1 = TableDefinition(
    name="cache_locks",
    columns={
        "cache_key": String(255).primary().comment("Lock Key"),
        "owner": String(255).nullable().comment("Lock Owner"),
        "expiration": Double().nullable().comment("Expiration"),
    },
    primary_key="cache_key",
    comment="Table to store atomic cache locks.",
)
