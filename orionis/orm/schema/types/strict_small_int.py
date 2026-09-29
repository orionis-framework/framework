from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class StrictSmallInt(ColumnDefinition):
    """The SQL ``SMALLINT`` type."""

    __slots__ = ()

    def __init__(self) -> None:
        """
        Initialize a SMALLINT column definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.SMALLINT)
