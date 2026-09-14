from orionis.database import Migration
from orionis.support.facades import Schema

class CreateModelHasRolesTable(Migration):

    async def up(self) -> None:
        """
        Create the ``model_has_roles`` table.

        Relates roles to any model through a polymorphic (morph) relation.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        async with Schema.create("model_has_roles") as table:
            table.bigInteger("role_id").foreign("roles.id").comment("Role ID")
            table.string("model_type", 255).comment("Model Class Name")
            table.string("model_id", 255).comment("Canonical Model ID")

            table.primaryKey("role_id", "model_id", "model_type")
            table.index("model_id", "model_type")
            table.comment("Table to relate roles with any model (morph).")

    async def down(self) -> None:
        """
        Drop the ``model_has_roles`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop("model_has_roles")
