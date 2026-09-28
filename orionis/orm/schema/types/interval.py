from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class Interval(ColumnDefinition):
    """A type for ``datetime.timedelta()`` objects."""

    __slots__ = ()

    def __init__(
        self,
        *,
        native: bool = True,
        second_precision: int | None = None,
        day_precision: int | None = None,
    ) -> None:
        """
        Construct an Interval object.

        Parameters
        ----------
        native : bool, optional
            Whether to use the backend's native ``INTERVAL`` type, when
            supported (PostgreSQL, Oracle Database).
        second_precision : int or None, optional
            Fractional seconds precision for native interval types.
        day_precision : int or None, optional
            Day precision for native interval types.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            ColumnType.INTERVAL,
            ColumnOptions(
                native=native,
                second_precision=second_precision,
                day_precision=day_precision,
            ),
        )
