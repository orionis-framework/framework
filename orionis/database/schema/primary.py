"""Describe a primary-key constraint on a table."""

class PrimaryKey:
    """Describe a primary-key constraint on a table."""

    def __init__(self, *columns: str) -> None:
        """Define a primary key constraint with one or more columns.

        Parameters
        ----------
        *columns : str
            Column names that compose the primary key.

        Attributes
        ----------
        columns : tuple of str
            The column names for the primary key.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self.columns: tuple[str, ...] = columns
        """The column names for the primary key."""
