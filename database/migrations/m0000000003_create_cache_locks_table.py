from database.schemas.cache_locks_v1 import CACHE_LOCKS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreateCacheLocksTable(Migration):

    async def up(self) -> None:
        """
        Create the ``cache_locks`` table used to store atomic cache locks.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(CACHE_LOCKS_V1)

    async def down(self) -> None:
        """
        Drop the ``cache_locks`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(CACHE_LOCKS_V1.name)
