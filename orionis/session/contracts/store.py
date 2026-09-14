from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.session.entities.record import SessionRecord

class ISessionStore(ABC):
    """
    Contract every session backing-store must satisfy.

    Responsibilities
    ----------------
    - Persist and retrieve ``SessionRecord`` objects.
    - Remove records on demand.
    - Reject updates to absent or expired records atomically.
    - Collect expired records via ``gc()``.

    The store is **not** responsible for:

    - Knowing about ``Request`` or ``Response``.
    - Generating session identifiers.
    - Creating ``Session`` objects.
    - Choosing the lifetime duration (the manager does that).
    """

    __slots__ = ()

    @abstractmethod
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

    @abstractmethod
    async def write(self, record: SessionRecord) -> None:
        """
        Persist *record*, creating or overwriting the existing entry.

        Parameters
        ----------
        record : SessionRecord
            The record to store.

        Returns
        -------
        None
        """

    @abstractmethod
    async def update(self, record: SessionRecord) -> bool:
        """Update a live session atomically without creating a missing record.

        Parameters
        ----------
        record : SessionRecord
            Replacement session payload and expiration.

        Returns
        -------
        bool
            True only when a live record was updated. Deletion or expiry
            must win over a stale request's write, including across workers.
        """

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """
        Remove the record for *session_id*; a no-op when absent.

        Parameters
        ----------
        session_id : str
            Unique session identifier to remove.

        Returns
        -------
        bool
            True if this call removed a record; False when already absent.
        """

    @abstractmethod
    async def gc(self) -> None:
        """
        Remove all records whose ``expires_at`` is in the past.

        Returns
        -------
        None
        """
