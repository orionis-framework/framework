from database.schemas.personal_access_tokens_v1 import PERSONAL_ACCESS_TOKENS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreatePersonalAccessTokensTable(Migration):

    async def up(self) -> None:
        """
        Create the ``personal_access_tokens`` table used by API auth.

        Only the SHA-256 digest of a token reaches this table, so a
        leaked row never exposes a usable credential.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(PERSONAL_ACCESS_TOKENS_V1)

    async def down(self) -> None:
        """
        Drop the ``personal_access_tokens`` table.

        Reverts the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(PERSONAL_ACCESS_TOKENS_V1.name)
