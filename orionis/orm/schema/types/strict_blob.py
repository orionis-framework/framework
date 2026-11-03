"""The SQL ``BLOB`` type."""

from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class StrictBlob(ColumnDefinition):
    """The SQL ``BLOB`` type."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __init__(self, length: int | None = None) -> None:
        """
        Construct a LargeBinary type.

        Parameters
        ----------
        length : int or None, optional
            Length for the column for use in DDL statements.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.BLOB, ColumnOptions(length=length))
