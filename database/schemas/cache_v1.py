from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Double, String, Text

CACHE_V1 = TableDefinition(
    name="cache",
    columns={
        "cache_key": String(255).primary().comment("Cache Key"),
        "cache_value": Text().nullable().comment("Cache Value"),
        "expiration": Double().nullable().comment("Expiration"),
    },
    primary_key="cache_key",
    comment="Table to store cache entries.",
)
