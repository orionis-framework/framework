from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class StrictTimestamp(ColumnDefinition):
    """The SQL ``TIMESTAMP`` type."""

    __slots__ = ()

    def __init__(self, *, timezone: bool = False) -> None:
        """
        Construct a new TIMESTAMP.

        Parameters
        ----------
        timezone : bool, optional
            Whether the TIMESTAMP type should enable timezone support,
            if available on the target database.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.TIMESTAMP, ColumnOptions(timezone=timezone))
