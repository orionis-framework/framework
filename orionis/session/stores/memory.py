from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from orionis.session.contracts.store import ISessionStore

if TYPE_CHECKING:
    from orionis.session.entities.record import SessionRecord

class MemorySessionStore(ISessionStore):
    """
    In-process session store backed by a plain dictionary.

    Suitable for development and testing.  The internal dictionary is
    instance-scoped: separate instances never share state.

    Notes
    -----
    Thread safety is not guaranteed.  Use this store only in single-
    threaded event-loop environments (the standard asyncio model).
    """

    __slots__ = ("_storage",)

    def __init__(self) -> None:
        """
        Initialise an empty in-memory session store.

        Returns
        -------
        None
        """
        self._storage: dict[str, SessionRecord] = {}

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
            The stored record, or ``None`` when absent.
        """
        record = self._storage.get(session_id)

        if record is None:
            return None

        if record.expires_at <= datetime.now(UTC):
            del self._storage[session_id]
            return None

        return deepcopy(record)

    async def write(self, record: SessionRecord) -> None:
        """
        Insert or replace the record keyed by its identifier.

        Parameters
        ----------
        record : SessionRecord
            The record to persist.

        Returns
        -------
        None
        """
        self._storage[record.id] = deepcopy(record)

    async def update(self, record: SessionRecord) -> bool:
        """Replace a live record without yielding between checking and writing.

        Parameters
        ----------
        record : SessionRecord
            Replacement record.

        Returns
        -------
        bool
            Whether a live session still existed at the time of the update.
        """
        previous = self._storage.get(record.id)
        if previous is None or previous.expires_at <= datetime.now(UTC):
            return False
        self._storage[record.id] = deepcopy(record)
        return True

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
            True only when a stored record was removed.
        """
        return self._storage.pop(session_id, None) is not None

    async def gc(self) -> None:
        """
        Evict all records whose ``expires_at`` is in the past.

        Collects expired keys before mutating the dictionary to avoid
        modifying a collection during iteration.

        Returns
        -------
        None
        """
        now = datetime.now(UTC)
        expired = [
            sid
            for sid, rec in self._storage.items()
            if rec.expires_at <= now
        ]
        for sid in expired:
            del self._storage[sid]
