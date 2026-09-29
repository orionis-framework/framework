from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class SchemaType(ColumnDefinition):
    """Adds schema-level DDL, mixed into :class:`Boolean`/:class:`Enum`."""

    __slots__ = ()

    def __init__(self, name: str | None = None) -> None:
        """
        Initialize the schema-type placeholder definition.

        Parameters
        ----------
        name : str or None, optional
            Name of the associated schema-level construct.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(ColumnType.SCHEMA_TYPE, ColumnOptions(constraint_name=name))
