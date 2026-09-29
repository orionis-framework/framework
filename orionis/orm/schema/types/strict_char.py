from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class StrictChar(ColumnDefinition):
    """The SQL ``CHAR`` type."""

    __slots__ = ()

    def __init__(
        self,
        length: int | None = None,
        collation: str | None = None,
    ) -> None:
        """
        Create a string-holding type.

        Parameters
        ----------
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            ColumnType.CHAR,
            ColumnOptions(length=length, collation=collation),
        )
