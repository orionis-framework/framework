# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Clear entries from a selected application cache store."""

import sys
from typing import ClassVar
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.exceptions import CacheException
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.output.console import Console
from orionis.database.exceptions import DatabaseException
from orionis.foundation.config.cache.enums.drivers import Drivers


class ClearCacheCommand(BaseCommand):
    """Clear entries from the named or default application cache store."""

    timestamps: bool = False
    """Timestamps flag used by ``ClearCacheCommand``."""
    signature: str = "clear:cache"
    """Signature identifier: ``clear:cache``."""
    description: str = "Clear the named or default application cache store."
    """Describe the cache cleanup operation."""
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="--store",
            type_=str,
            choices=tuple(driver.value for driver in Drivers),
            default=None,
            help="Select the cache store to clear. Defaults to the configured store.",
        ),
    ]
    """Declare the optional cache store selection."""

    async def handle(self, cache: ICacheManager, console: Console) -> int:
        """
        Clear the selected cache store and report the result.

        Parameters
        ----------
        cache : orionis.cache.contracts.ICacheManager
            Cache manager for the running application.
        console : orionis.console.Console
            Console used to report the operation result.

        Returns
        -------
        int
            Zero when the store is cleared; one when the backend fails.
        """
        store = self.getArgument("store")
        try:
            target = cache.store(store) if store is not None else cache
            cleared = await target.clear()
        except Exception as error:
            # Exception instances retain the native SDK class identity; their
            # defining modules are already loaded by the selected backend.
            backend_errors = tuple(
                getattr(module, name)
                for module_name, name in (
                    ("aiomcache.exceptions", "ClientException"),
                    ("redis.exceptions", "RedisError"),
                    ("sqlalchemy.exc", "SQLAlchemyError"),
                )
                if (  # NOSONAR(S1110) - Assign before comparing with None.
                    module := sys.modules.get(module_name)
                )
                is not None
            )
            if not isinstance(
                error,
                (CacheException, DatabaseException, OSError, *backend_errors),
            ):
                raise
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

        label = "Application cache" if store is None else f"Cache store '{store}'"
        console.success(f"{label} cleared.", timestamp=False)
        return 0
