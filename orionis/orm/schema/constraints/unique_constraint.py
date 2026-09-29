from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class UniqueConstraint:
    """
    Composite ``UNIQUE`` constraint spanning one or more columns.

    Attributes
    ----------
    columns : tuple of str
        Column names covered by the constraint, in declaration order.
    name : str or None
        Explicit constraint name, or ``None`` to let the engine assign one.
    """

    columns: tuple[str, ...]
    name: str | None = None
