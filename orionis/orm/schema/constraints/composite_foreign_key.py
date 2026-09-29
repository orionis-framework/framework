from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CompositeForeignKey:
    """
    Multi-column foreign key constraint.

    Attributes
    ----------
    columns : tuple of str
        Local column names, in the same order as ``ref_columns``.
    ref_table : str
        Name of the referenced table.
    ref_columns : tuple of str
        Referenced column names, aligned positionally with ``columns``.
    name : str or None
        Explicit constraint name, or ``None`` to let the engine assign one.
    """

    columns: tuple[str, ...]
    ref_table: str
    ref_columns: tuple[str, ...]
    name: str | None = None
