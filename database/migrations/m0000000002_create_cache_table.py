from database.schemas.cache_v1 import CACHE_V1
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
        await Schema.createFromDefinition(CACHE_V1)

    async def down(self) -> None:
        """
        Drop the ``cache`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(CACHE_V1.name)
