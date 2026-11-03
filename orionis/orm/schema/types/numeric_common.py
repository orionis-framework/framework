"""
Share a common base for numeric column types.

Used by :class:`orionis.orm.schema.types.Numeric` and
:class:`orionis.orm.schema.types.Float`.
"""

from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class NumericCommon(ColumnDefinition):
    """
    Share a common base for numeric column types.

    Used by :class:`orionis.orm.schema.types.Numeric` and
    :class:`orionis.orm.schema.types.Float`.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __init__(self) -> None:
        """
        Initialize the numeric-common placeholder definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.NUMERIC_COMMON)
