from database.schemas.sessions_v1 import SESSIONS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreateSessionsTable(Migration):

    async def up(self) -> None:
        """
        Create the ``sessions`` table used to store session records.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(SESSIONS_V1)

    async def down(self) -> None:
        """
        Drop the ``sessions`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(SESSIONS_V1.name)
