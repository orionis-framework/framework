from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.database.schema.column import Column
from orionis.database.schema.comment import Comment
from orionis.database.schema.foreign import ForeignKey
from orionis.database.schema.index import Index
from orionis.database.schema.primary import PrimaryKey
from orionis.database.schema.unique import Unique

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.orm.schema.column import ColumnDefinition

class Blueprint:
    """
    Fluent collector of column definitions for a single table.

    Instances are yielded by ``Schema.create(name)`` when used as an
    async context manager (``async with schema.create(name) as table:``),
    allowing columns to be declared one call at a time instead of passing
    every definition up front. Table-level constraints (``Comment``,
    ``ForeignKey``, ``Index``, ``PrimaryKey``, ``Unique``) are declared the
    same way, via ``table.comment(...)``, ``table.foreignKey(...)``,
    ``table.index(...)``, ``table.primaryKey(...)`` and
    ``table.unique(...)``.
    """

    __slots__ = ("__columns", "__constraints", "__factory_cache")

    def __init__(self) -> None:
        """
        Initialize the blueprint with no columns declared yet.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__columns: list[ColumnDefinition] = []
        self.__constraints: list[
            Comment | ForeignKey | Index | PrimaryKey | Unique
        ] = []
        self.__factory_cache: dict[str, Callable[..., ColumnDefinition]] = {}

    def __getattr__(self, name: str) -> Callable[..., ColumnDefinition]:
        """
        Proxy a column-factory call to :class:`Column`, recording it.

        This is what powers calls such as ``table.string("username")`` or
        ``table.boolean("is_admin")``: any factory exposed by
        :class:`Column` becomes available on the blueprint, and the
        resulting column is appended to this table automatically.

        Parameters
        ----------
        name : str
            Name of the ``Column`` factory method being invoked.

        Returns
        -------
        Callable[..., ColumnDefinition]
            Wrapper that builds the column and appends it to this table.

        Raises
        ------
        AttributeError
            If ``name`` does not match a known ``Column`` factory method.
        """
        # Reuse a previously resolved factory for this column-type name.
        cached = self.__factory_cache.get(name)
        if cached is not None:
            return cached

        factory = getattr(Column, name, None)
        if factory is None or not callable(factory):
            error_msg = f"'{type(self).__name__}' object has no attribute {name!r}."
            raise AttributeError(error_msg)

        def _build(*args: object, **kwargs: object) -> ColumnDefinition:
            """Build the column via ``Column`` and register it on the table."""
            column = factory(*args, **kwargs)
            self.__columns.append(column)
            return column

        self.__factory_cache[name] = _build
        return _build

    def timestamps(self, *, timezone: bool = False) -> None:
        """
        Add nullable ``created_at`` and ``updated_at`` columns.

        Parameters
        ----------
        timezone : bool, optional
            Whether the timestamp columns should be timezone-aware.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.dateTime("created_at", timezone=timezone).nullable()
        self.dateTime("updated_at", timezone=timezone).nullable()

    def comment(self, text: str) -> Comment:
        """
        Attach a table-level comment.

        Parameters
        ----------
        text : str
            The comment text content.

        Returns
        -------
        Comment
            The constraint recorded on this blueprint.
        """
        definition = Comment(text)
        self.__constraints.append(definition)
        return definition

    def foreignKey(
        self,
        column: str,
        ref_table: str,
        ref_column: str,
        name: str | None = None,
    ) -> ForeignKey:
        """
        Declare a foreign key constraint on this table.

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
        ForeignKey
            The constraint recorded on this blueprint.
        """
        definition = ForeignKey(column, ref_table, ref_column, name=name)
        self.__constraints.append(definition)
        return definition

    def index(
        self,
        *columns: str,
        name: str | None = None,
        unique: bool = False,
    ) -> Index:
        """
        Declare an index over one or more columns.

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
        Index
            The constraint recorded on this blueprint.
        """
        definition = Index(*columns, name=name, unique=unique)
        self.__constraints.append(definition)
        return definition

    def primaryKey(self, *columns: str) -> PrimaryKey:
        """
        Declare a (composite) primary key over one or more columns.

        Parameters
        ----------
        columns : str
            Column names that compose the primary key.

        Returns
        -------
        PrimaryKey
            The constraint recorded on this blueprint.
        """
        definition = PrimaryKey(*columns)
        self.__constraints.append(definition)
        return definition

    def unique(self, *columns: str, name: str | None = None) -> Unique:
        """
        Declare a unique constraint over one or more columns.

        Parameters
        ----------
        columns : str
            Column names to apply the unique constraint to.
        name : str | None, optional
            Name of the unique constraint. If not provided, a default
            name will be generated.

        Returns
        -------
        Unique
            The constraint recorded on this blueprint.
        """
        definition = Unique(*columns, name=name)
        self.__constraints.append(definition)
        return definition

    def columns(self) -> tuple[ColumnDefinition, ...]:
        """
        Return the columns declared so far, in declaration order.

        Returns
        -------
        tuple of ColumnDefinition
            Snapshot of every column recorded on this blueprint.
        """
        return tuple(self.__columns)

    def definitions(
        self,
    ) -> tuple[
        ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique, ...,
    ]:
        """
        Return every column and table-level constraint declared so far.

        Returns
        -------
        tuple
            Columns followed by constraints, in the order each group was
            recorded on this blueprint.
        """
        return (*self.__columns, *self.__constraints)
