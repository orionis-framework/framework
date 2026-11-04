"""Create the framework authentication tables without removing data."""

from orionis.auth.authorization.schema import build_authorization_tables
from orionis.auth.passwords.schema import build_password_reset_table
from orionis.auth.tokens.schema import build_tokens_table
from orionis.console.base.command import BaseCommand
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import DatabaseException, QueryException
from orionis.foundation.contracts.application import IApplication

class AuthMigrateCommand(BaseCommand):
    """Create the framework authentication tables without removing data."""

    # ruff: noqa: TC001

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    timestamps: bool = False
    """Timestamps flag used by ``AuthMigrateCommand``."""
    signature: str = "auth:migrate"
    """Signature identifier: ``auth:migrate``."""
    description: str = (
        "Create framework authorization, access token, and password reset tables."
    )
    """Description of the authentication storage preparation command."""

    async def handle(self, app: IApplication, manager: IConnectionManager) -> int:
        """
        Create authorization and credentials on the default SQL connection.

        Parameters
        ----------
        app : orionis.IApplication
            Application exposing the configured access and password-reset tables.
        manager : orionis.database.contracts.IConnectionManager
            Manager resolving the default SQL connection for authentication storage.

        Returns
        -------
        int
            Zero on success or one for connection or schema creation errors.
        """
        try:
            connection = manager.connection()
            if not connection.supportsUniqueConstraints():
                message = "Authentication storage requires enforced unique constraints."
                raise QueryException(message)
            token_table: str = (
                app.config("auth.tokens.table") or "personal_access_tokens"
            )
            reset_table: str = (
                app.config("auth.passwords.table") or "password_reset_tokens"
            )
            tables = (
                *build_authorization_tables(),
                build_tokens_table(token_table),
                build_password_reset_table(reset_table),
            )
            if len({table.name.casefold() for table in tables}) != len(tables):
                message = (
                    "Authentication storage table names must be distinct, "
                    "ignoring case."
                )
                raise QueryException(message)
            for table in tables:
                await connection.createTable(table)
        except DatabaseException as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success("Auth tables migrated successfully.", timestamp=False)
        return 0
