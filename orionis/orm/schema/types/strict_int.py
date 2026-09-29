from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class StrictInt(ColumnDefinition):
    """Alias of ``INTEGER``."""

    __slots__ = ()

    def __init__(self) -> None:
        """
        Initialize an INT column definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.INT)
