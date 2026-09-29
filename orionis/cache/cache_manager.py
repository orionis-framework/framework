from pathlib import Path
from typing import TYPE_CHECKING, Any
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.exceptions import CacheStoreException
from orionis.cache.repository import CacheRepository
from orionis.cache.stores.database import build as _build_database
from orionis.cache.stores.file import FileCacheBackend
from orionis.cache.stores.memcached import build as _build_memcached
from orionis.cache.stores.memory import build as _build_memory
from orionis.cache.stores.redis import build as _build_redis
from orionis.foundation.config.cache.entities.cache import Cache as _CacheConfig
from orionis.foundation.config.cache.enums.drivers import Drivers
from orionis.foundation.contracts.application import IApplication
from orionis.orm.resolver import ConnectionResolver

if TYPE_CHECKING:
    from collections.abc import Callable

class CacheManager(ICacheManager):

    # ruff: noqa: ANN401, TC001

    __slots__ = (
        "_app",
        "_base_path",
        "_config",
        "_default",
        "_prefix",
        "_repositories",
    )

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the manager and resolve the active cache configuration.

        Parameters
        ----------
        app : IApplication
            Application container used to read config and the base path.
        """
        self._app = app
        self._base_path: Path = app.basePath

        config_data: dict = app.config("cache")
        self._config = (
            _CacheConfig(**config_data)
            if isinstance(config_data, dict)
            else config_data
        )

        self._default: str = str(self._config.default)
        self._prefix: str = str(self._config.prefix)
        self._repositories: dict[str, CacheRepository] = {}

    # ── Store resolution ────────────────────────────────────────────────────

    def store(self, name: str | None = None) -> CacheRepository:
        """
        Return the :class:`CacheRepository` for the named (or default) store.

        The repository is created on first access and cached for reuse.

        Parameters
        ----------
        name : str | None
            Store name (``'file'``, ``'memory'``, ``'redis'``, ``'memcached'``).
            Defaults to the configured default store.

        Returns
        -------
        CacheRepository

        Raises
        ------
        CacheStoreException
            When the requested store is not configured.
        """
        resolved: str = name or self._default
        if resolved in self._repositories:
            return self._repositories[resolved]

        backend = self._buildBackend(resolved)
        repo = CacheRepository(backend=backend, prefix=self._prefix)
        self._repositories[resolved] = repo
        return repo

    def _buildBackend(self, name: str) -> Any:
        """
        Instantiate and return the raw backend for *name*.

        Parameters
        ----------
        name : str
            Driver name (``'file'``, ``'memory'``, ``'redis'``,
            ``'memcached'``).

        Returns
        -------
        Any
            Configured backend instance.

        Raises
        ------
        CacheStoreException
            When *name* is ``'redis'`` or ``'memcached'`` but the store
            is not configured.
        """
        stores = self._config.stores

        if name == Drivers.MEMORY.value:
            return _build_memory()

        if name == Drivers.REDIS.value:
            cfg = getattr(stores, "redis", None)
            if cfg is None:
                msg = "Redis store is not configured."
                raise CacheStoreException(msg)
            return _build_redis(
                endpoint=getattr(cfg, "endpoint", None) or "127.0.0.1",
                port=int(getattr(cfg, "port", 6379)),
                db=int(getattr(cfg, "db", 0)),
                password=getattr(cfg, "password", None) or None,
            )

        if name == Drivers.MEMCACHED.value:
            cfg = getattr(stores, "memcached", None)
            if cfg is None:
                msg = "Memcached store is not configured."
                raise CacheStoreException(msg)
            return _build_memcached(
                endpoint=getattr(cfg, "endpoint", None) or "127.0.0.1",
                port=int(getattr(cfg, "port", 11211)),
            )

        if name == Drivers.DATABASE.value:
            return self._buildDatabaseBackend()

        # Default: file driver
        cfg = getattr(stores, "file", None)
        raw_path: str = (
            getattr(cfg, "path", "storage/framework/cache/data")
            if cfg is not None
            else "storage/framework/cache/data"
        )
        resolved_path = Path(raw_path)
        if not resolved_path.is_absolute():
            resolved_path = self._base_path / resolved_path

        return FileCacheBackend(path=resolved_path)

    def _buildDatabaseBackend(self) -> Any:
        """
        Instantiate and return the database cache backend.

        Returns
        -------
        Any
            Configured :class:`DatabaseCacheBackend` instance.

        Raises
        ------
        CacheStoreException
            When the database store is not configured.
        """
        cfg = getattr(self._config.stores, "database", None)
        if cfg is None:
            msg = "Database store is not configured."
            raise CacheStoreException(msg)

        return _build_database(
            connection=ConnectionResolver.connection(
                getattr(cfg, "connection", None),
            ),
            table=str(getattr(cfg, "table", None) or "cache"),
            lock_table=getattr(cfg, "lock_table", None),
        )

    # ── Default-store proxy ─────────────────────────────────────────────────

    async def get(self, key: str) -> Any:
        """
        Retrieve the value for *key* from the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Any
            Cached value, or ``None`` when absent.
        """
        return await self.store().get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Store *value* under *key* in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            Value to cache.
        ttl : float | None
            Time-to-live in seconds.  ``None`` means no expiry.

        Returns
        -------
        bool
            ``True`` on success.
        """
        return await self.store().set(key, value, ttl=ttl)

    async def has(self, key: str) -> bool:
        """
        Check whether *key* exists and has not expired in the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        bool
            ``True`` if the key is present and valid.
        """
        return await self.store().has(key)

    async def delete(self, key: str) -> bool:
        """
        Remove *key* from the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        bool
            ``True`` if the key existed, ``False`` otherwise.
        """
        return await self.store().delete(key)

    async def clear(self) -> bool:
        """
        Remove all entries from the default store.

        Returns
        -------
        bool
            ``True`` on success.
        """
        return await self.store().clear()

    async def getMany(self, keys: list[str]) -> dict[str, Any]:
        """
        Retrieve multiple values from the default store.

        Parameters
        ----------
        keys : list[str]
            Cache keys to fetch.

        Returns
        -------
        dict[str, Any]
            Mapping of key → value; missing keys map to ``None``.
        """
        return await self.store().getMany(keys)

    async def setMany(
        self,
        values: dict[str, Any],
        ttl: float | None = None,
    ) -> bool:
        """
        Store multiple key/value pairs in the default store.

        Parameters
        ----------
        values : dict[str, Any]
            Mapping of key → value.
        ttl : float | None
            Shared TTL in seconds.

        Returns
        -------
        bool
            ``True`` on success.
        """
        return await self.store().setMany(values, ttl=ttl)

    async def remember(
        self,
        key: str,
        ttl: float | None,
        resolver: Callable,
    ) -> Any:
        """
        Return the cached value for *key*; resolve and cache if absent.

        Parameters
        ----------
        key : str
            Cache key.
        ttl : float | None
            TTL applied when caching the resolved value.
        resolver : Callable
            Zero-argument callable (sync or async) producing the value.

        Returns
        -------
        Any
            Cached or freshly computed value.
        """
        return await self.store().remember(key, ttl, resolver)

    async def rememberForever(self, key: str, resolver: Callable) -> Any:
        """
        Return the cached value for *key*; resolve and cache forever if absent.

        Parameters
        ----------
        key : str
            Cache key.
        resolver : Callable
            Zero-argument callable (sync or async) producing the value.

        Returns
        -------
        Any
            Cached or freshly computed value.
        """
        return await self.store().rememberForever(key, resolver)

    async def pull(self, key: str) -> Any:
        """
        Return and immediately delete *key* from the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Any
            Cached value, or ``None`` when absent.
        """
        return await self.store().pull(key)

    async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Store *value* only if *key* is absent in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            Value to store.
        ttl : float | None
            Optional TTL in seconds.

        Returns
        -------
        bool
            ``True`` on success, ``False`` when the key already exists.
        """
        return await self.store().add(key, value, ttl=ttl)

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment the integer at *key* by *amount* in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        amount : int
            Amount to add.

        Returns
        -------
        int
            New value after increment.
        """
        return await self.store().increment(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement the integer at *key* by *amount* in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        amount : int
            Amount to subtract.

        Returns
        -------
        int
            New value after decrement.
        """
        return await self.store().decrement(key, amount)

    def lock(self, key: str, timeout: float | None = None) -> Any:
        """
        Return an async context-manager lock for *key* on the default store.

        Parameters
        ----------
        key : str
            Resource key to lock.
        timeout : float | None
            Maximum lock duration in seconds.

        Returns
        -------
        CacheLock
            Async context manager.
        """
        return self.store().lock(key, timeout)
