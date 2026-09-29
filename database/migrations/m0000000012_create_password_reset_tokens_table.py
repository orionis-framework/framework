from database.schemas.password_reset_tokens_v1 import PASSWORD_RESET_TOKENS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreatePasswordResetTokensTable(Migration):

    async def up(self) -> None:
        """Create the reset token store.

        Timestamps use UTC Unix seconds.

        Returns
        -------
        None
            The reset token table is created as a side effect.
        """
        await Schema.createFromDefinition(PASSWORD_RESET_TOKENS_V1)

    async def down(self) -> None:
        """Remove the reset token store.

        Returns
        -------
        None
            The reset token table is removed as a side effect.
        """
        # Drop the reset token table.
        await Schema.drop(PASSWORD_RESET_TOKENS_V1.name)
