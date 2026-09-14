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
        async with Schema.create("personal_access_tokens") as table:
            table.id().comment("Token ID")
            table.string("tokenable_type", 255).comment("Owner Class Name")
            table.string("tokenable_id", 255).comment("Canonical Owner ID")
            table.string("name", 255).comment("Token Label")
            table.string("token", 64).unique().comment("SHA-256 Digest")
            table.text("abilities").nullable().comment("Granted Abilities")
            table.dateTime("last_used_at").nullable().comment("Last Used At")
            table.dateTime("expires_at").nullable().index().comment("Expires At")
            table.dateTime("revoked_at").nullable().index().comment("Revoked At")
            table.timestamps()

            table.index("tokenable_type", "tokenable_id")
            table.comment("Table to store personal access tokens.")

    async def down(self) -> None:
        """
        Drop the ``personal_access_tokens`` table.

        Reverts the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop("personal_access_tokens")
