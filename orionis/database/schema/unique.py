"""Describe a uniqueness constraint on table columns."""

from orionis.orm.schema.constraints import UniqueConstraint


class Unique:
    """Describe a uniqueness constraint on table columns."""

    def __init__(self, *columns: str, name: str | None = None) -> None:
        """
        Define a unique constraint for database columns.

        Parameters
        ----------
        *columns : str
            Column names to apply the unique constraint to.
        name : str | None, optional
            Name of the unique constraint. If not provided, a default name
            will be generated.

        Returns
        -------
        None
            No return value.
        """
        self.constraint = UniqueConstraint(columns=columns, name=name)
        """Constraint produced by ``UniqueConstraint``."""
