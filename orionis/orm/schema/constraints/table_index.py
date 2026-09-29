from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TableIndex:
    """
    Composite index spanning one or more columns.

    Attributes
    ----------
    columns : tuple of str
        Column names covered by the index, in declaration order.
    name : str or None
        Explicit index name, or ``None`` to derive one from the table.
    unique : bool
        Whether the index also enforces uniqueness.
    """

    columns: tuple[str, ...]
    name: str | None = None
    unique: bool = False
