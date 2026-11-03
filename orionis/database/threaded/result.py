"""Retain materialized Core results without exposing a live DBAPI cursor."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from sqlalchemy.engine import CursorResult

class ThreadedResult:
    """Retain materialized Core results without exposing a live DBAPI cursor."""

    __slots__ = ("_result", "inserted_primary_key", "rowcount")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, result: CursorResult[Any]) -> None:
        """
        Buffer rows and generated-key metadata on the connection's worker.

        Parameters
        ----------
        result : ``sqlalchemy.engine.CursorResult[Any]``
            Live Core result to consume and close before releasing its connection.

        Returns
        -------
        None
            Store a memory-only result with the original row count and key.
        """
        try:
            self.rowcount = result.rowcount
            """Rowcount obtained from ``result.rowcount``."""
            self.inserted_primary_key = (
                tuple(result.inserted_primary_key)
                if result.is_insert and not result.context.executemany
                else None
            )
            """Primary-key values returned for the inserted row."""
            self._result = result.freeze()() if result.returns_rows else None
            """Live Core result to consume and close before releasing its connection."""
        finally:
            result.close()

    def mappings(self) -> Iterable[Mapping[str, Any]]:
        """
        Expose materialized rows without another driver call.

        Returns
        -------
        collections.abc.Iterable[collections.abc.Mapping[str, typing.Any]]
            Column-keyed rows retained in memory.
        """
        return self._result.mappings() if self._result is not None else ()

    def scalar(self) -> object:
        """Return the first column of the first materialized row.

        Returns
        -------
        object
            First value, or None when there are no rows.
        """
        return self._result.scalar() if self._result is not None else None
