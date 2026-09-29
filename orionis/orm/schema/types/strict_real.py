from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class StrictReal(ColumnDefinition):
    """The SQL ``REAL`` type."""

    __slots__ = ()

    def __init__(
        self,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> None:
        """
        Construct a Float.

        Parameters
        ----------
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        asdecimal : bool, optional
            Whether values are coerced to ``decimal.Decimal``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            ColumnType.REAL,
            ColumnOptions(
                precision=precision,
                as_decimal=asdecimal,
                decimal_return_scale=decimal_return_scale,
            ),
        )
