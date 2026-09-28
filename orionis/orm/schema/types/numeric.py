from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class Numeric(ColumnDefinition):
    """Base for non-integer numeric types, such as ``NUMERIC``/``DECIMAL``."""

    __slots__ = ()

    def __init__(
        self,
        precision: int | None = None,
        scale: int | None = None,
        decimal_return_scale: int | None = None,
        *,
        asdecimal: bool = True,
    ) -> None:
        """
        Construct a Numeric.

        Parameters
        ----------
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        scale : int or None, optional
            Numeric scale for use in DDL ``CREATE TABLE``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.
        asdecimal : bool, optional
            Whether values are returned as ``decimal.Decimal`` objects.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If precision or scale are negative or inconsistent.
        """
        # Validate the numeric shape early to fail fast at class definition.
        if precision is not None or scale is not None:
            valid_types = isinstance(precision, int) and isinstance(scale, int)
            if not valid_types or precision <= 0 or scale < 0 or scale > precision:
                error_msg = (
                    "Numeric requires a positive precision and a non-negative "
                    "scale not greater than the precision."
                )
                raise ValueError(error_msg)
        super().__init__(
            ColumnType.NUMERIC,
            ColumnOptions(
                precision=precision,
                scale=scale,
                decimal_return_scale=decimal_return_scale,
                as_decimal=asdecimal,
            ),
        )
