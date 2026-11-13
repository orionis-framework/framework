"""Describe a database index and its indexed columns."""

from orionis.orm.schema.constraints import TableIndex


class Index:
    """Describe a database index and its indexed columns."""

    def __init__(
        self,
        *columns: str,
        name: str | None = None,
        unique: bool = False,
    ) -> None:
        """
        Create an index for database columns.

        Parameters
        ----------
        columns : str
            Column names to include in the index.
        name : str | None, optional
            Name of the index. If not provided, a default name will be
            generated.
        unique : bool, optional
            Whether the index should enforce uniqueness. Default is False.

        Returns
        -------
        None
            No return value.
        """
        # Initialize index with provided columns and configuration.
        self.constraint = TableIndex(columns=columns, name=name, unique=unique)
        """Initialize index with provided columns and configuration."""
