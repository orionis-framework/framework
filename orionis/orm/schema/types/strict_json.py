from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class StrictJson(ColumnDefinition):
    """Represent a SQL ``JSON`` type."""

    __slots__ = ()

    def __init__(self, *, none_as_null: bool = False) -> None:
        """
        Construct a JSON type.

        Parameters
        ----------
        none_as_null : bool, optional
            When ``True``, persist Python ``None`` as SQL ``NULL`` instead
            of the JSON encoding of ``null``.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.JSON, ColumnOptions(none_as_null=none_as_null))
