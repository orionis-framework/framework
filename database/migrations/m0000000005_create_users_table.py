from database.schemas.users_v1 import USERS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreateUsersTable(Migration):

    async def up(self) -> None:
        """
        Create the ``users`` table used to store application users.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(USERS_V1)

    async def down(self) -> None:
        """
        Drop the ``users`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(USERS_V1.name)
