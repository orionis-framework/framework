"""Declare a non-integer numeric column using the logical ``NUMERIC`` kind."""

from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType


class Numeric(ColumnDefinition):
    """Declare a non-integer numeric column using the logical ``NUMERIC`` kind."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

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
            Numeric precision for DDL. Supply it together with scale, or
            leave both values as None.
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
            If the shape is incomplete, contains non-integers or booleans,
            or has non-positive precision or scale outside its range.
        """
        # Validate the numeric shape early to fail fast at class definition.
        if precision is not None or scale is not None:
            valid_types = (
                isinstance(precision, int)
                and not isinstance(precision, bool)
                and isinstance(scale, int)
                and not isinstance(scale, bool)
            )
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
