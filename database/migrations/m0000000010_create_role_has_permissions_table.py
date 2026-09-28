from database.schemas.role_has_permissions_v1 import ROLE_HAS_PERMISSIONS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreateRoleHasPermissionsTable(Migration):

    async def up(self) -> None:
        """
        Create the ``role_has_permissions`` table.

        Relates roles with permissions.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(ROLE_HAS_PERMISSIONS_V1)

    async def down(self) -> None:
        """
        Drop the ``role_has_permissions`` table.

        Reverts the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(ROLE_HAS_PERMISSIONS_V1.name)
