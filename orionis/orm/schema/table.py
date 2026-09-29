from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.orm.schema.column import ColumnDefinition
    from orionis.orm.schema.constraints import (
        CompositeForeignKey,
        TableIndex,
        UniqueConstraint,
    )

@dataclass(frozen=True, slots=True, eq=False)
class TableDefinition:
    """
    Framework-agnostic description of a database table.

    Built once per model by the metaclass and consumed by the database
    compiler to produce engine-specific SQL. It carries no reference to
    the underlying SQL toolkit.

    Attributes
    ----------
    name : str
        Logical table name without any connection prefix.
    columns : dict of str to ColumnDefinition
        Column definitions keyed by attribute name.
    primary_key : str
        Name of the primary key column, when it is a single column.
    schema : str or None
        Database schema owning the table, or ``None`` for the default.
    comment : str or None
        Descriptive comment rendered alongside the table DDL.
    composite_primary_key : tuple of str or None
        Column names forming a multi-column primary key. When set, it
        takes precedence over the single-column ``primary_key``.
    unique_constraints : tuple of UniqueConstraint
        Composite ``UNIQUE`` constraints spanning multiple columns.
    foreign_keys : tuple of CompositeForeignKey
        Multi-column foreign key constraints.
    indexes : tuple of TableIndex
        Composite indexes spanning multiple columns.
    """

    name: str
    columns: dict[str, ColumnDefinition] = field(default_factory=dict)
    primary_key: str = "id"
    schema: str | None = None
    comment: str | None = None
    composite_primary_key: tuple[str, ...] | None = None
    unique_constraints: tuple[UniqueConstraint, ...] = ()
    foreign_keys: tuple[CompositeForeignKey, ...] = ()
    indexes: tuple[TableIndex, ...] = ()

    def columnNames(self) -> tuple[str, ...]:
        """
        Return the declared column names in definition order.

        Returns
        -------
        tuple of str
            Ordered column names.
        """
        return tuple(self.columns)

    def hasColumn(self, name: str) -> bool:
        """
        Report whether a column is declared on the table.

        Parameters
        ----------
        name : str
            Column name to look up.

        Returns
        -------
        bool
            ``True`` when the column exists in the definition.
        """
        return name in self.columns
