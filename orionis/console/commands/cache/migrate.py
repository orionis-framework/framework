"""Create the configured framework cache tables without removing data."""

from orionis.cache.exceptions import CacheStoreException
from orionis.cache.stores.database import DatabaseCacheBackend
from orionis.console.base.command import BaseCommand
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import DatabaseException
from orionis.foundation.contracts.application import IApplication

class CacheMigrateCommand(BaseCommand):
    """Create the configured framework cache tables without removing data."""

    # ruff: noqa: TC001

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    timestamps: bool = False
    """Timestamps flag used by ``CacheMigrateCommand``."""
    signature: str = "cache:migrate"
    """Signature identifier: ``cache:migrate``."""
    description: str = "Create the configured database cache and lock tables."
    """
    Description identifier: ``Create the configured database cache and lock
    tables.``.
    """

    async def handle(self, app: IApplication, manager: IConnectionManager) -> int:
        """
        Create database cache storage independently of the active cache driver.

        Parameters
        ----------
        app : orionis.IApplication
            Application exposing the database cache configuration.
        manager : orionis.database.contracts.IConnectionManager
            Manager resolving the cache store's SQL connection.

        Returns
        -------
        int
            Zero on success or one for missing configuration or database errors.
        """
        try:
            if app.config("cache.stores.database") is None:
                message = "Database cache store is not configured."
                raise CacheStoreException(message)
            backend = DatabaseCacheBackend(
                manager.connection(app.config("cache.stores.database.connection")),
                table=app.config("cache.stores.database.table") or "cache",
                lock_table=app.config("cache.stores.database.lock_table"),
            )
            await backend.migrate()
        except (DatabaseException, CacheStoreException) as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success("Cache tables migrated successfully.", timestamp=False)
        return 0
