from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class Integer(ColumnDefinition):
    """A type for ``int`` integers."""

    __slots__ = ()

    def __init__(self) -> None:
        """
        Initialize an integer column definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.INTEGER)
