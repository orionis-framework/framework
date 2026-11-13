"""
Describe the schema-level placeholder kind.

The SQL compiler rejects this placeholder as a concrete column type.
"""

from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType


class SchemaType(ColumnDefinition):
    """
    Describe the schema-level placeholder kind.

    The SQL compiler rejects this placeholder as a concrete column type.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

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
