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
        async with Schema.create("role_has_permissions") as table:
            table.bigInteger("permission_id").foreign("permissions.id").comment("Permission ID")
            table.bigInteger("role_id").foreign("roles.id").comment("Role ID")
            table.primaryKey("permission_id", "role_id")
            table.index("role_id", "permission_id")

            table.comment("Table to relate roles with permissions.")

    async def down(self) -> None:
        """
        Drop the ``role_has_permissions`` table.

        Reverts the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop("role_has_permissions")
