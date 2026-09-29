from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.orm.schema.column import ColumnDefinition

class DefinitionBucket:
    """Mutable accumulator used while classifying schema definitions."""

    __slots__ = (
        "columns",
        "foreign_keys",
        "indexes",
        "kwargs",
        "primary_columns",
        "unique_constraints",
    )

    def __init__(self) -> None:
        """
        Initialize empty containers for each definition kind.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.columns: dict[str, ColumnDefinition] = {}
        self.primary_columns: list[str] = []
        self.unique_constraints: list[object] = []
        self.foreign_keys: list[object] = []
        self.indexes: list[object] = []
        self.kwargs: dict[str, object] = {}
