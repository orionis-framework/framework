from database.schemas.roles_v1 import ROLES_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreateRolesTable(Migration):

    async def up(self) -> None:
        """
        Create the ``roles`` table used to store role names.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(ROLES_V1)

    async def down(self) -> None:
        """
        Drop the ``roles`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(ROLES_V1.name)
