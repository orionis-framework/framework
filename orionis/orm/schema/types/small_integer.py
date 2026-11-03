"""A type for smaller ``int`` integers. Typically generates ``SMALLINT``."""

from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class SmallInteger(ColumnDefinition):
    """A type for smaller ``int`` integers. Typically generates ``SMALLINT``."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __init__(self) -> None:
        """
        Initialize a small integer column definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.SMALL_INTEGER)
