from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.cache import (
    Cache, Database, Drivers, File, Memcached, Memory, Redis, Stores,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapCache(Cache):
    # ----------------------------------------------------------------------------------
    # default : Drivers | str, optional
    # --- The default cache store driver.
    # --- Defaults to the CACHE_STORE env var or "file" if not set.
    # ----------------------------------------------------------------------------------
    default: Drivers | str = field(
        default_factory=lambda: Env.get("CACHE_STORE", Drivers.FILE),
    )

    # ----------------------------------------------------------------------------------
    # prefix : str, optional
    # --- Global key prefix applied to all cache entries.
    # ----------------------------------------------------------------------------------
    prefix: str = field(
        default_factory=lambda: Env.get("CACHE_PREFIX", ""),
    )

    # ----------------------------------------------------------------------------------
    # stores : Stores | dict, optional
    # --- Configuration for all available cache backends.
    # ----------------------------------------------------------------------------------
    stores: Stores | dict = field(
        default_factory=lambda: Stores(
            # --------------------------------------------------------------------------
            # file : File, optional
            # --- File-based cache store (default driver).
            # --------------------------------------------------------------------------
            file=File(
                path=Env.get("CACHE_FILE_PATH", "storage/framework/cache/data"),
            ),
            # --------------------------------------------------------------------------
            # memory : Memory, optional
            # --- In-memory cache store (no persistence, process-scoped).
            # --------------------------------------------------------------------------
            memory=Memory(),
            # --------------------------------------------------------------------------
            # redis : Redis, optional
            # --- Redis cache store.
            # --------------------------------------------------------------------------
            redis=Redis(
                endpoint=Env.get("REDIS_HOST", "127.0.0.1"),
                port=Env.get("REDIS_PORT", 6379),
                db=Env.get("REDIS_DB", 0),
                password=Env.get("REDIS_PASSWORD", None),
            ),
            # --------------------------------------------------------------------------
            # memcached : Memcached, optional
            # --- Memcached cache store.
            # --------------------------------------------------------------------------
            memcached=Memcached(
                endpoint=Env.get("MEMCACHED_HOST", "127.0.0.1"),
                port=Env.get("MEMCACHED_PORT", 11211),
            ),
            # --------------------------------------------------------------------------
            # database : Database, optional
            # --- Database cache store.
            # --------------------------------------------------------------------------
            database=Database(
                connection=Env.get("DB_CACHE_CONNECTION", None),
                table=Env.get("DB_CACHE_TABLE", "cache"),
                lock_table=Env.get("DB_CACHE_LOCK_TABLE", "cache_locks"),
            ),
        ),
    )
