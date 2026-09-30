from orionis.database.contracts.schema import ISchema
from orionis.database.schema.comment import Comment
from orionis.database.schema.foreign import ForeignKey
from orionis.database.schema.index import Index
from orionis.database.schema.primary import PrimaryKey
from orionis.database.schema.table_creation import TableCreation
from orionis.database.schema.unique import Unique
from orionis.orm.schema.column import ColumnDefinition
from orionis.orm.model import Model
from orionis.orm.schema.table import TableDefinition

class Schema(ISchema):

    @staticmethod
    def connection(name: str | None = None) -> type[Schema]:
        ...

    @staticmethod
    def create(
        name: str,
        *definitions: (
            ColumnDefinition
            | Comment
            | ForeignKey
            | Index
            | PrimaryKey
            | Unique
        ),
    ) -> TableCreation:
        ...

    @staticmethod
    async def createFromDefinition(definition: TableDefinition) -> bool:
        ...

    @staticmethod
    async def createFromModel(model: type[Model]) -> bool:
        ...

    @staticmethod
    async def drop(name: str) -> bool:
        ...
