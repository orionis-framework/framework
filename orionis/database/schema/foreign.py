from orionis.orm.schema.constraints import CompositeForeignKey

class ForeignKey:

    def __init__(
        self,
        column: str,
        ref_table: str,
        ref_column: str,
        name: str | None = None,
    ) -> None:
        """
        Initialize a foreign key constraint.

        Parameters
        ----------
        column : str
            The local column name.
        ref_table : str
            The referenced table name.
        ref_column : str
            The referenced column name.
        name : str | None, optional
            The constraint name. Defaults to None.

        Returns
        -------
        None
        """
        # Create a composite foreign key wrapper for single column
        self.foreign = CompositeForeignKey(
            columns=(column,),
            ref_table=ref_table,
            ref_columns=(ref_column,),
            name=name,
        )
