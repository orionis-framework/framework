"""Mutable accumulator used while classifying schema definitions."""

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
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self) -> None:
        """
        Initialize empty containers for each definition kind.

        Returns
        -------
        None
            No return value.
        """
        self.columns: dict[str, ColumnDefinition] = {}
        """Column definitions included in the table schema."""
        self.primary_columns: list[str] = []
        """Columns included in the primary-key constraint."""
        self.unique_constraints: list[object] = []
        """Uniqueness constraints declared for the table."""
        self.foreign_keys: list[object] = []
        """Foreign-key constraints declared for the table."""
        self.indexes: list[object] = []
        """Indexes declared for the table."""
        self.kwargs: dict[str, object] = {}
        """Keyword options forwarded to construction of the underlying object."""
