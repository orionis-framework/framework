from database.schemas.permissions_v1 import PERMISSIONS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreatePermissionsTable(Migration):

    async def up(self) -> None:
        """
        Create the ``permissions`` table used to store permission names.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(PERMISSIONS_V1)

    async def down(self) -> None:
        """
        Drop the ``permissions`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(PERMISSIONS_V1.name)
