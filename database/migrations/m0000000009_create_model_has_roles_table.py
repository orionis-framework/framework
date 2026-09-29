from database.schemas.model_has_roles_v1 import MODEL_HAS_ROLES_V1
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
        await Schema.createFromDefinition(MODEL_HAS_ROLES_V1)

    async def down(self) -> None:
        """
        Drop the ``model_has_roles`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(MODEL_HAS_ROLES_V1.name)
