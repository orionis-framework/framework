from aiomcache.exceptions import ClientException
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.exceptions import CacheException
from orionis.console.base.command import BaseCommand
from orionis.console.output.console import Console
from orionis.database.exceptions import DatabaseException

class ClearCacheCommand(BaseCommand):
    """Clear entries from the application's configured default cache store."""

    # ruff: noqa: TC001

    timestamps: bool = False
    signature: str = "clear:cache"
    description: str = "Clear entries from the default application cache store."

    async def handle(self, cache: ICacheManager, console: Console) -> int:
        """
        Clear the configured default cache store.

        Parameters
        ----------
        cache : ICacheManager
            Cache manager for the running application.
        console : Console
            Console used to report the operation result.

        Returns
        -------
        int
            Zero when the store is cleared; one when the backend fails.
        """
        try:
            cleared = await cache.clear()
        except (
            CacheException,
            ClientException,
            DatabaseException,
            OSError,
            RedisError,
            SQLAlchemyError,
        ) as error:
            console.error(
                "The application cache could not be cleared "
                f"({type(error).__name__}: {error}).",
                timestamp=False,
            )
            return 1

        if not cleared:
            console.error(
                "The application cache could not be cleared.",
                timestamp=False,
            )
            return 1

        console.success("Application cache cleared.", timestamp=False)
        return 0
