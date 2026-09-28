from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class BigInteger(ColumnDefinition):
    """A type for bigger ``int`` integers. Typically generates ``BIGINT``."""

    __slots__ = ()

    def __init__(self) -> None:
        """
        Initialize a big integer column definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.BIG_INTEGER)
