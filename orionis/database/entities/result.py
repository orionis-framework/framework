from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class InsertResult:
    """
    Outcome of an INSERT statement executed through a connection.

    Attributes
    ----------
    last_insert_id : Any
        Primary key generated for the inserted row, or ``None`` when the
        driver cannot report it (for example on multi-row inserts).
    row_count : int
        Number of rows affected by the statement.
    """

    last_insert_id: Any
    row_count: int
