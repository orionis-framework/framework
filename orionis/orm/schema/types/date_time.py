from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class DateTime(ColumnDefinition):
    """A type for ``datetime.datetime()`` objects."""

    __slots__ = ()

    def __init__(self, *, timezone: bool = False) -> None:
        """
        Construct a new DateTime.

        Parameters
        ----------
        timezone : bool, optional
            Whether the datetime type should enable timezone support, if
            available on the base date/time-holding type.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.DATETIME, ColumnOptions(timezone=timezone))
