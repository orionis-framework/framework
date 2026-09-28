from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class StrictArray(ColumnDefinition):
    """Represent a SQL ``ARRAY`` type."""

    __slots__ = ()

    def __init__(
        self,
        item_type: ColumnDefinition,
        *,
        as_tuple: bool = False,
        dimensions: int | None = None,
        zero_indexes: bool = False,
    ) -> None:
        """
        Construct an ARRAY.

        Parameters
        ----------
        item_type : ColumnDefinition
            Column definition of the array elements.
        as_tuple : bool, optional
            Whether results are converted to tuples instead of lists.
        dimensions : int or None, optional
            Fixed number of dimensions, when not ``None``.
        zero_indexes : bool, optional
            Whether to convert between zero- and one-based indexes.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            ColumnType.ARRAY,
            ColumnOptions(
                item_type=item_type,
                as_tuple=as_tuple,
                dimensions=dimensions,
                zero_indexes=zero_indexes,
            ),
        )
