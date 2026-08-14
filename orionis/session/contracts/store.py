from __future__ import annotations
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
    - Collect expired records via ``gc()``.

    The store is **not** responsible for:

    - Knowing about ``Request`` or ``Response``.
    - Generating session identifiers.
    - Creating ``Session`` objects.
    - Enforcing expiry policy (the manager does that).
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
    async def delete(self, session_id: str) -> None:
        """
        Remove the record for *session_id*; a no-op when absent.

        Parameters
        ----------
        session_id : str
            Unique session identifier to remove.

        Returns
        -------
        None
        """

    @abstractmethod
    async def gc(self) -> None:
        """
        Remove all records whose ``expires_at`` is in the past.

        Returns
        -------
        None
        """
