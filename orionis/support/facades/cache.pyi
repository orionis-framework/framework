# ruff: noqa: ANN401
# Cache operations accept and return arbitrary stored values.
from collections.abc import Callable
from typing import Any
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.locks.lock import CacheLock
from orionis.cache.repository import CacheRepository
from orionis.container.facades.facade import Facade

class Cache(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[ICacheManager]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> ICacheManager: ...

    @classmethod
    def store(cls, name: str | None = None) -> CacheRepository: ...

    @classmethod
    async def get(cls, key: str) -> Any: ...

    @classmethod
    async def set(cls, key: str, value: Any, ttl: float | None = None) -> bool: ...

    @classmethod
    async def has(cls, key: str) -> bool: ...

    @classmethod
    async def delete(cls, key: str) -> bool: ...

    @classmethod
    async def clear(cls) -> bool: ...

    @classmethod
    async def getMany(cls, keys: list[str]) -> dict[str, Any]: ...

    @classmethod
    async def setMany(
        cls,
        values: dict[str, Any],
        ttl: float | None = None,
    ) -> bool: ...

    @classmethod
    async def remember(
        cls,
        key: str,
        ttl: float | None,
        resolver: Callable[[], object],
    ) -> Any: ...

    @classmethod
    async def rememberOnce(
        cls,
        key: str,
        ttl: float | None,
        resolver: Callable[[], object],
        *,
        wait_timeout: float = 10,
        lease: float | None = None,
    ) -> Any: ...

    @classmethod
    async def rememberForever(cls, key: str, resolver: Callable[[], object]) -> Any: ...

    @classmethod
    async def pull(cls, key: str) -> Any: ...

    @classmethod
    async def add(cls, key: str, value: Any, ttl: float | None = None) -> bool: ...

    @classmethod
    async def increment(cls, key: str, amount: int = 1) -> int: ...

    @classmethod
    async def decrement(cls, key: str, amount: int = 1) -> int: ...

    @classmethod
    def lock(cls, key: str, timeout: float | None = None) -> CacheLock: ...
