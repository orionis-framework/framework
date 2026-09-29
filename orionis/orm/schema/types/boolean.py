from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class Boolean(ColumnDefinition):
    """A bool datatype, typically ``BOOLEAN`` or ``SMALLINT`` in DDL."""

    __slots__ = ()

    def __init__(
        self,
        *,
        create_constraint: bool = False,
        name: str | None = None,
    ) -> None:
        """
        Construct a Boolean.

        Parameters
        ----------
        create_constraint : bool, optional
            When the boolean is emulated as int/smallint, also create a
            CHECK constraint ensuring 1 or 0 as a value.
        name : str or None, optional
            Name of the CHECK constraint, when generated.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            ColumnType.BOOLEAN,
            ColumnOptions(create_constraint=create_constraint, constraint_name=name),
        )
