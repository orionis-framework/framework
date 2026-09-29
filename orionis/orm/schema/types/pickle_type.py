from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class PickleType(ColumnDefinition):
    """Holds Python objects, serialized using ``pickle``."""

    __slots__ = ()

    def __init__(
        self,
        protocol: int = 5,
        pickler: object | None = None,
        impl: object | None = None,
    ) -> None:
        """
        Construct a PickleType.

        Parameters
        ----------
        protocol : int, optional
            Pickle protocol, defaults to ``pickle.HIGHEST_PROTOCOL``.
        pickler : object or None, optional
            Object exposing pickle-compatible ``dumps``/``loads`` methods.
        impl : object or None, optional
            Binary-storing type used in place of the default ``LargeBinary``.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            ColumnType.PICKLE_TYPE,
            ColumnOptions(protocol=protocol, pickler=pickler, impl=impl),
        )
