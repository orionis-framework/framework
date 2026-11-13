# ruff: noqa: TC001
# Expose cache contract types to runtime dependency injection.

"""Session store backed by the framework's cache system."""

from datetime import UTC, datetime
from typing import Any
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.contracts.repository import ICacheRepository
from orionis.session.contracts.store import ISessionStore
from orionis.session.entities.record import SessionRecord

# Namespace prefix keeping session entries away from unrelated cache keys.
_KEY_PREFIX: str = "session:"
"""Namespace prefix keeping session entries away from unrelated cache keys."""


class CacheSessionStore(ISessionStore):
    """
    Session store backed by the framework's cache system.

    Persist each session as one cache entry. Truncate its remaining TTL to
    whole seconds so rounding cannot prolong the record's deadline. This can
    expire a record up to one second early; deadlines less than one full
    second away cannot be persisted or renewed. Actual eviction timing still
    depends on the backend, its clock and transport latency.

    Notes
    -----
    ``ICacheManager`` exposes no way to enumerate stored keys, so this
    store cannot (and does not need to) implement an active
    :meth:`orionis.session.stores.cache.CacheSessionStore.gc`:
    the backend enforces expiration. Physical removal of stale entries depends
    on that backend's cleanup policy and may occur only when they are read.
    """

    __slots__ = ("_repository",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, cache: ICacheManager, store: str | None = None) -> None:
        """
        Bind the store to the requested (or default) cache repository.

        Parameters
        ----------
        cache : orionis.cache.contracts.ICacheManager
            The application's cache manager.
        store : str | None, optional
            Name of the cache store to use.  ``None`` selects the
            configured default store.

        Returns
        -------
        None
            No return value.
        """
        self._repository: ICacheRepository = cache.store(store)
        """Repository produced by ``cache.store``."""

    async def read(self, session_id: str) -> SessionRecord | None:
        """
        Return the stored record for *session_id*, or ``None``.

        Parameters
        ----------
        session_id : str
            Unique session identifier to look up.

        Returns
        -------
        orionis.session.entities.record.SessionRecord | None
            The stored record, or ``None`` when absent or expired.
        """
        payload: dict[str, Any] | None = await self._repository.get(
            _KEY_PREFIX + session_id,
        )

        if not isinstance(payload, dict) or payload.get("id") != session_id:
            return None
        expiration = payload.get("expires_at")
        if isinstance(expiration, str):
            try:
                expiration = datetime.fromisoformat(expiration)
            except ValueError:
                return None
        if (
            not isinstance(expiration, datetime)
            or expiration.tzinfo is None
            or expiration <= datetime.now(UTC)
            or not isinstance(payload.get("data"), dict)
        ):
            return None

        return SessionRecord(
            id=payload["id"],
            data=payload["data"],
            expires_at=expiration,
        )

    async def write(self, record: SessionRecord) -> None:
        """
        Insert or replace the record keyed by its identifier.

        The cache entry's TTL is derived from ``record.expires_at``; a
        record with less than one full second remaining is deleted instead.

        Parameters
        ----------
        record : orionis.session.entities.record.SessionRecord
            The record to persist.

        Returns
        -------
        None
            No return value.
        """
        ttl = int((record.expires_at - datetime.now(UTC)).total_seconds())

        if ttl <= 0:
            await self.delete(record.id)
            return

        payload = {
            "id": record.id,
            "data": record.data,
            "expires_at": record.expires_at,
        }
        await self._repository.set(_KEY_PREFIX + record.id, payload, ttl=ttl)

    async def update(self, record: SessionRecord) -> bool:
        """
        Replace a live cache session without recreating a missing key.

        Parameters
        ----------
        record : orionis.session.entities.record.SessionRecord
            Replacement record.

        Returns
        -------
        bool
            Whether the cache atomically replaced a live record. Return False
            when the replacement has less than one full second remaining.
        """
        ttl = int((record.expires_at - datetime.now(UTC)).total_seconds())
        if ttl <= 0:
            return False
        return await self._repository.replace(
            _KEY_PREFIX + record.id,
            {
                "id": record.id,
                "data": record.data,
                "expires_at": record.expires_at,
            },
            ttl=ttl,
        )

    async def delete(self, session_id: str) -> bool:
        """
        Remove the record for *session_id* (no-op when absent).

        Parameters
        ----------
        session_id : str
            Unique session identifier to remove.

        Returns
        -------
        bool
            True only when an entry was deleted.
        """
        return await self._repository.delete(_KEY_PREFIX + session_id)

    async def gc(self) -> None:
        """
        Leave expiration cleanup to the cache backend's TTL.

        Returns
        -------
        None
            No return value.
        """
