from orionis.database import Migration
from orionis.support.facades import Schema

class CreateUsersTable(Migration):

    async def up(self) -> None:
        """
        Create the ``users`` table used to store application users.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        async with Schema.create("users") as table:
            table.id().comment("User ID")
            table.string("name", 255).comment("Full Name")
            table.string("email", 255).unique().comment("Email Address")
            table.dateTime("email_verified_at").nullable().comment("Email Verification Timestamp")
            table.string("password", 255).comment("Hashed Password")
            table.string("remember_token", 100).nullable().comment("Remember Me Token")
            table.boolean("active").default(value=True).comment("Active Status")
            table.timestamps()

            table.comment("Table to store application users.")

    async def down(self) -> None:
        """
        Drop the ``users`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop("users")
