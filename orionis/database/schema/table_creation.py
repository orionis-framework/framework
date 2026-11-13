# ruff: noqa: E402, SLF001, TC001, TC003
# Share the schema creation boundary and expose traceback annotations at runtime.
# Resolve the schema module after defining its context to preserve the cyclic API.
"""Async context manager returned by ``Schema.create``."""

from types import TracebackType
from orionis.database.schema.blueprint import Blueprint


class TableCreation:
    """
    Async context manager returned by ``Schema.create``.

    ``async with schema.create(name) as table:`` yields a
    :class:`orionis.database.schema.Blueprint` so columns can
    be declared inside the block; the table is created on exit unless
    the block raised an exception.
    """

    __slots__ = ("__blueprint", "__name", "__schema")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        schema: schema_module.Schema,
        name: str,
    ) -> None:
        """
        Store the pending table declaration request.

        Parameters
        ----------
        schema : orionis.database.schema.schema.Schema
            The schema instance that will perform the creation.
        name : str
            The name of the table to create.

        Returns
        -------
        None
            No return value.
        """
        self.__schema = schema
        """The schema instance that will perform the creation."""
        self.__name = name
        """The name of the table to create."""
        self.__blueprint: Blueprint | None = None
        """Table blueprint being converted into a schema operation."""

    async def __aenter__(self) -> Blueprint:
        """
        Start a fluent, per-table column declaration block.

        Returns
        -------
        orionis.database.schema.Blueprint
            Collector used to declare columns via method calls.

        Raises
        ------
        RuntimeError
            If this context already owns an unfinished declaration.
        """
        if self.__blueprint is not None:
            message = "This table declaration is already active."
            raise RuntimeError(message)
        self.__blueprint = Blueprint()
        return self.__blueprint

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """
        Create the table with the collected columns, unless it raised.

        Parameters
        ----------
        exc_type : type[BaseException] or None
            The exception type raised inside the block, if any.
        exc : BaseException or None
            The exception instance raised inside the block, if any.
        traceback : types.TracebackType or None
            The traceback for the raised exception, if any.

        Returns
        -------
        bool
            ``False`` to always propagate exceptions raised in the block.
        """
        blueprint = self.__blueprint
        self.__blueprint = None
        if exc_type is None and blueprint is not None:
            await self.__schema._createTable(
                self.__name,
                blueprint.definitions(),
            )
        return False


import orionis.database.schema.schema as schema_module
