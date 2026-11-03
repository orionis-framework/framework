from orionis.auth.tokens.schema import build_tokens_table
from orionis.console.base.command import BaseCommand
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import DatabaseException, QueryException
from orionis.foundation.contracts.application import IApplication

class AuthMigrateCommand(BaseCommand):
    """Create the framework personal access token table without removing data."""

    # ruff: noqa: TC001

    __slots__ = ()

    timestamps: bool = False
    signature: str = "auth:migrate"
    description: str = "Create the configured personal access token table."

    async def handle(self, app: IApplication, manager: IConnectionManager) -> int:
        """
        Create token storage on the application's default SQL connection.

        Parameters
        ----------
        app : IApplication
            Application exposing the configured personal access token table.
        manager : IConnectionManager
            Manager resolving the default SQL connection used by token queries.

        Returns
        -------
        int
            Zero on success or one for connection or schema creation errors.
        """
        try:
            connection = manager.connection()
            if not connection.supportsUniqueConstraints():
                message = "Personal access tokens require enforced unique constraints."
                raise QueryException(message)
            table = app.config("auth.tokens.table") or "personal_access_tokens"
            await connection.createTable(build_tokens_table(table))
        except DatabaseException as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success("Auth token table migrated successfully.", timestamp=False)
        return 0
