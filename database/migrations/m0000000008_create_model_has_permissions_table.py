from database.schemas.model_has_permissions_v1 import MODEL_HAS_PERMISSIONS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreateModelHasPermissionsTable(Migration):

    async def up(self) -> None:
        """
        Create the ``model_has_permissions`` table.

        Relates permissions to any model through a polymorphic (morph)
        relation.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(MODEL_HAS_PERMISSIONS_V1)

    async def down(self) -> None:
        """
        Drop the ``model_has_permissions`` table.

        Reverts the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(MODEL_HAS_PERMISSIONS_V1.name)
