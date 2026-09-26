from orionis.database import Migration
from orionis.support.facades import Schema

class CreatePasswordResetTokensTable(Migration):
    """Keep one expiring reset credential per email on the identity connection."""

    async def up(self) -> None:
        """Create the reset token store.

        Timestamps use UTC Unix seconds.

        Returns
        -------
        None
            The reset token table is created as a side effect.
        """
        # Define the reset token table columns.
        async with Schema.create("password_reset_tokens") as table:
            table.string("email", 255).primary()
            table.string("token", 64).nullable()
            table.string("user_id", 255)
            table.string("password_fingerprint", 64)
            table.bigInteger("created_at").index()

            table.index("token")
            table.comment("Store for password reset tokens, one per email.")

    async def down(self) -> None:
        """Remove the reset token store.

        Returns
        -------
        None
            The reset token table is removed as a side effect.
        """
        # Drop the reset token table.
        await Schema.drop("password_reset_tokens")
