# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from collections.abc import Awaitable
from contextlib import AbstractAsyncContextManager
from typing import Protocol
from orionis.container.facades.facade import Facade
from orionis.database.contracts.schema import ISchema
from orionis.database.schema.blueprint import Blueprint
from orionis.database.schema.table_creation import TableCreation
from orionis.orm.model import Model
from orionis.orm.schema.table import TableDefinition

class _TableCreationDispatch(
    Awaitable[TableCreation],
    AbstractAsyncContextManager[Blueprint, bool],
    Protocol,
): ...

class Schema(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[ISchema]:
        """Return the schema service contract."""

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> ISchema:
        """Resolve a schema service from the container."""

    @classmethod
    def connection(cls, name: str | None = None) -> Awaitable[ISchema]:
        """Set the connection name for schema operations."""

    @classmethod
    def create(cls, name: str) -> _TableCreationDispatch:
        """Start a fluent table declaration block."""

    @classmethod
    def createFromDefinition(cls, definition: TableDefinition) -> Awaitable[bool]:
        """Create a table from its reusable, versioned definition."""

    @classmethod
    def createFromModel(cls, model: type[Model]) -> Awaitable[bool]:
        """Create the current schema declared by a concrete model."""

    @classmethod
    def drop(cls, name: str) -> Awaitable[bool]:
        """Drop an existing table."""
