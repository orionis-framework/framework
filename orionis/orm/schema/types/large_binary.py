"""A type for large binary byte data, such as ``BLOB``/``BYTEA``."""

from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType


class LargeBinary(ColumnDefinition):
    """A type for large binary byte data, such as ``BLOB``/``BYTEA``."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __init__(self, length: int | None = None) -> None:
        """
        Construct a LargeBinary type.

        Parameters
        ----------
        length : int or None, optional
            Length for the column for use in DDL statements, for those
            binary types that accept a length.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the length is not a positive non-boolean integer or None.
        """
        if length is not None and (
            not isinstance(length, int) or isinstance(length, bool) or length <= 0
        ):
            error_msg = "LargeBinary length must be a positive integer or None."
            raise ValueError(error_msg)
        super().__init__(ColumnType.LARGE_BINARY, ColumnOptions(length=length))
