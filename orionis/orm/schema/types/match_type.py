from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType

class MatchType(ColumnDefinition):
    """Refers to the return type of the ``MATCH`` operator."""

    __slots__ = ()

    def __init__(self) -> None:
        """
        Initialize a match type column definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.MATCH_TYPE)
