from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class NumericCommon(ColumnDefinition):
    """Common mixin placeholder shared by :class:`Numeric` and :class:`Float`."""

    __slots__ = ()

    def __init__(self) -> None:
        """
        Initialize the numeric-common placeholder definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.NUMERIC_COMMON)
