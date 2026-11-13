# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from orionis.database.contracts.schema import ISchema
from orionis.database.schema.table_creation import TableCreation
from orionis.orm.model import Model
from orionis.orm.schema.table import TableDefinition

class Schema(ISchema):
    @staticmethod
    def connection(name: str | None = None) -> ISchema:
        """Set the connection name for schema operations."""

    @staticmethod
    def create(name: str) -> TableCreation:
        """Start a fluent table declaration block."""

    @staticmethod
    async def createFromDefinition(definition: TableDefinition) -> bool:
        """Create a table from its reusable, versioned definition."""

    @staticmethod
    async def createFromModel(model: type[Model]) -> bool:
        """Create the current schema declared by a concrete model."""

    @staticmethod
    async def drop(name: str) -> bool:
        """Drop an existing table."""
