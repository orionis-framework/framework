"""A type for ``datetime.date()`` objects."""

from __future__ import annotations
from datetime import date
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types.column_type import ColumnType


class Date[TValue = date](ColumnDefinition[TValue]):
    """A type for ``datetime.date()`` objects."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __init__(self) -> None:
        """
        Initialize a date column definition.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.DATE)
