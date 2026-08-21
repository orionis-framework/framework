from orionis.database import Migration
from orionis.support.facades import Schema

class CreateCacheTable(Migration):

    async def up(self) -> None:
        """
        Create the ``cache`` table used to store cache entries.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        async with Schema.create("cache") as table:
            table.string("cache_key", 255).primary().comment("Cache Key")
            table.text("cache_value").nullable().comment("Cache Value")
            table.double("expiration").nullable().comment("Expiration")

            table.comment("Table to store cache entries.")

    async def down(self) -> None:
        """
        Drop the ``cache`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop("cache")
