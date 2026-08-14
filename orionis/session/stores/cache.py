from datetime import UTC, datetime
from typing import Any
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.contracts.repository import ICacheRepository
from orionis.session.contracts.store import ISessionStore
from orionis.session.entities.record import SessionRecord

# Namespace prefix keeping session entries away from unrelated cache keys.
_KEY_PREFIX: str = "session:"

class CacheSessionStore(ISessionStore):
    """
    Session store backed by the framework's cache system.

    Each session is persisted as a single cache entry whose TTL mirrors
    ``record.expires_at``.  Expiry is therefore delegated entirely to the
    underlying cache backend (file, database, Redis, ...); no in-process
    bookkeeping or manual sweeping is required.

    Notes
    -----
    ``ICacheManager`` exposes no way to enumerate stored keys, so this
    store cannot (and does not need to) implement an active :meth:`gc`:
    the backend evicts expired entries on its own.
    """

    # ruff: noqa: TC001

    __slots__ = ("_repository",)

    def __init__(self, cache: ICacheManager, store: str | None = None) -> None:
        """
        Bind the store to the requested (or default) cache repository.

        Parameters
        ----------
        cache : ICacheManager
            The application's cache manager.
        store : str | None, optional
            Name of the cache store to use.  ``None`` selects the
            configured default store.

        Returns
        -------
        None
        """
        self._repository: ICacheRepository = cache.store(store)

    async def read(self, session_id: str) -> SessionRecord | None:
        """
        Return the stored record for *session_id*, or ``None``.

        Parameters
        ----------
        session_id : str
            Unique session identifier to look up.

        Returns
        -------
        SessionRecord | None
            The stored record, or ``None`` when absent or expired.
        """
        payload: dict[str, Any] | None = await self._repository.get(
            _KEY_PREFIX + session_id,
        )

        if payload is None:
            return None

        return SessionRecord(
            id=payload["id"],
            data=payload["data"],
            expires_at=payload["expires_at"],
        )

    async def write(self, record: SessionRecord) -> None:
        """
        Insert or replace the record keyed by its identifier.

        The cache entry's TTL is derived from ``record.expires_at``; a
        record that has already expired is deleted instead of written.

        Parameters
        ----------
        record : SessionRecord
            The record to persist.

        Returns
        -------
        None
        """
        ttl = (record.expires_at - datetime.now(UTC)).total_seconds()

        if ttl <= 0:
            await self.delete(record.id)
            return

        payload = {
            "id": record.id,
            "data": record.data,
            "expires_at": record.expires_at,
        }
        await self._repository.set(_KEY_PREFIX + record.id, payload, ttl=ttl)

    async def delete(self, session_id: str) -> None:
        """
        Remove the record for *session_id* (no-op when absent).

        Parameters
        ----------
        session_id : str
            Unique session identifier to remove.

        Returns
        -------
        None
        """
        await self._repository.delete(_KEY_PREFIX + session_id)

    async def gc(self) -> None:
        """
        No-op: expiry is enforced natively by the cache backend's TTL.

        Returns
        -------
        None
        """

