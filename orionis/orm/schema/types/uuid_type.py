from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class Uuid(ColumnDefinition):
    """Represent a database agnostic UUID datatype."""

    __slots__ = ()

    def __init__(
        self,
        *,
        as_uuid: bool = True,
        native_uuid: bool = True,
    ) -> None:
        """
        Construct a Uuid type.

        Parameters
        ----------
        as_uuid : bool, optional
            Whether values are interpreted as Python ``uuid.UUID`` objects.
        native_uuid : bool, optional
            Whether to use the backend's native UUID-storing type.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            ColumnType.UUID,
            ColumnOptions(as_uuid=as_uuid, native_uuid=native_uuid),
        )
