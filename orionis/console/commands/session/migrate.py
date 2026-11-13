# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Create the configured framework session table without removing data."""

from orionis.console.base.command import BaseCommand
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import DatabaseException
from orionis.foundation.contracts.application import IApplication
from orionis.session.stores.database import DatabaseSessionStore


class SessionMigrateCommand(BaseCommand):
    """Create the configured framework session table without removing data."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    timestamps: bool = False
    """Timestamps flag used by ``SessionMigrateCommand``."""
    signature: str = "session:migrate"
    """Signature identifier: ``session:migrate``."""
    description: str = "Create the configured database session table."
    """Description identifier: ``Create the configured database session table.``."""

    async def handle(self, app: IApplication, manager: IConnectionManager) -> int:
        """
        Create session storage from the framework's internal definition.

        Parameters
        ----------
        app : orionis.IApplication
            Application exposing the session table and SQL connection settings.
        manager : orionis.database.contracts.IConnectionManager
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
