from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types._constants import DEFAULT_STRING_LENGTH
from orionis.orm.schema.types.column_type import ColumnType

class String(ColumnDefinition):
    """The base for all string and character types. In SQL, ``VARCHAR``."""

    __slots__ = ()

    def __init__(
        self,
        length: int | None = DEFAULT_STRING_LENGTH,
        collation: str | None = None,
    ) -> None:
        """
        Create a string-holding type.

        Parameters
        ----------
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the length is not a positive integer or None.
        """
        if length is not None and (not isinstance(length, int) or length <= 0):
            error_msg = "String length must be a positive integer or None."
            raise ValueError(error_msg)
        super().__init__(
            ColumnType.STRING,
            ColumnOptions(length=length, collation=collation),
        )
