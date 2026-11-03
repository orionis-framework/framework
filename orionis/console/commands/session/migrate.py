from orionis.console.base.command import BaseCommand
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import DatabaseException
from orionis.foundation.contracts.application import IApplication
from orionis.session.stores.database import DatabaseSessionStore

class SessionMigrateCommand(BaseCommand):
    """Create the configured framework session table without removing data."""

    # ruff: noqa: TC001

    __slots__ = ()

    timestamps: bool = False
    signature: str = "session:migrate"
    description: str = "Create the configured database session table."

    async def handle(self, app: IApplication, manager: IConnectionManager) -> int:
        """
        Create session storage from the framework's internal definition.

        Parameters
        ----------
        app : IApplication
            Application exposing the session table and SQL connection settings.
        manager : IConnectionManager
            Manager resolving the configured SQL connection.

        Returns
        -------
        int
            Zero on success or one for connection or schema creation errors.
        """
        try:
            store = DatabaseSessionStore(
                manager.connection(app.config("session.connection")),
                table=app.config("session.table") or "sessions",
            )
            await store.migrate()
        except DatabaseException as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success("Session table migrated successfully.", timestamp=False)
        return 0
