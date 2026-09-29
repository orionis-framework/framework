from __future__ import annotations
from abc import abstractmethod, ABC
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from orionis.database.schema.table_creation import TableCreation
    from orionis.orm.model import Model
    from orionis.orm.schema.table import TableDefinition

class ISchema(ABC):

    __slots__ = ()

    @abstractmethod
    def connection(self, name: str | None = None) -> Self:
        """
        Set the connection name for schema operations.

        Parameters
        ----------
        name : str | None, optional
            The connection name to use, by default None.

        Returns
        -------
        Self
            The current Schema instance for method chaining.

        Raises
        ------
        ValueError
            If connection name has already been defined.
        """
        ...

    @abstractmethod
    def create(
        self,
        name: str,
    ) -> TableCreation:
        """
        Start a fluent table declaration block with ``async with``.

        The block yields a ``Blueprint`` so columns can be declared
        fluently; the table is created after the block exits successfully.

        Parameters
        ----------
        name : str
            The name of the table to create. If the table belongs to a
            non-default schema, use the ``schema.table`` format.

        Returns
        -------
        TableCreation
            Async context manager that collects definitions and creates
            the table after a successful block.
        """

    @abstractmethod
    async def createFromDefinition(self, definition: TableDefinition) -> bool:
        """
        Create a table from a reusable, versioned schema definition.

        Parameters
        ----------
        definition : TableDefinition
            Definition shared by a model and a historical migration.

        Returns
        -------
        bool
            Whether table creation completed successfully.
        """

    @abstractmethod
    async def createFromModel(self, model: type[Model]) -> bool:
        """
        Create the current table declared by a concrete model.

        Parameters
        ----------
        model : type of Model
            Model providing precompiled table and connection metadata.

        Returns
        -------
        bool
            Whether table creation completed successfully.
        """

    @abstractmethod
    async def drop(self, name: str) -> bool:
        """
        Drop an existing table.

        Parameters
        ----------
        name : str
            The name of the table to drop. If the table belongs to a
            non-default schema, use the ``schema.table`` format.

        Returns
        -------
        bool
            ``True`` when the table is dropped without errors.
        """
