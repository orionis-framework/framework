from typing import TYPE_CHECKING
from orionis.schemas.rule import Rule

if TYPE_CHECKING:
    from orionis.orm.query.expressions import SelectPlan

class Unique(Rule):
    """
    Ensure a value is not already stored in a database column.

    Validation awaits the current connection and preserves its event loop
    and active transaction.
    """

    # ruff: noqa: ARG002, PLC0415, PLR0913

    __message__ = "Value must be unique."
    __code__ = "unique"

    __slots__ = ("_column", "_connection", "_ignore", "_ignore_column", "_table")

    def __init__(
        self,
        table: str,
        column: str,
        *,
        ignore: object = None,
        ignore_column: str = "id",
        connection: str | None = None,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the database table and column to check.

        Parameters
        ----------
        table : str
            Logical table name, without the connection prefix.
        column : str
            Column name within the table.
        ignore : object, optional
            Row identifier excluded from the lookup, so updating a record
            does not clash with itself.
        ignore_column : str, optional
            Column ``ignore`` is matched against.
        connection : str | None, optional
            Named connection to query, or ``None`` for the default one.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.
        """
        super().__init__(message=message)
        self._table: str = table
        self._column: str = column
        self._ignore: object = ignore
        self._ignore_column: str = ignore_column
        self._connection: str | None = connection

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Check uniqueness on the current loop and its active transaction.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value searched for in the configured column.
        instance : object
            Schema instance owning the field.

        Returns
        -------
        bool
            Whether no conflicting row is visible to the current connection.
        """
        if value is None:
            return True

        from orionis.orm.resolver import ConnectionResolver

        plan = self.__plan(value)
        connection = ConnectionResolver.connection(self._connection)
        return not bool(await connection.select(plan))

    def __plan(self, value: object) -> SelectPlan:
        """
        Build the query plan probing for a conflicting row.

        Parameters
        ----------
        value : object
            Value searched for in the configured column.

        Returns
        -------
        SelectPlan
            Plan matching at most one row that breaks uniqueness.
        """
        from orionis.orm.query.raw_builder import RawQueryBuilder

        builder = RawQueryBuilder().table(self._table)
        builder.where(self._column, "=", value)

        # Exclude the row being updated so it never clashes with itself.
        if self._ignore is not None:
            builder.where(self._ignore_column, "!=", self._ignore)

        plan = builder.toPlan()
        plan.limit_value = 1
        return plan
