from orionis.database.schema.comment import Comment
from orionis.database.schema.foreign import ForeignKey
from orionis.database.schema.index import Index
from orionis.database.schema.primary import PrimaryKey
from orionis.database.schema.unique import Unique
from orionis.orm.schema.column import ColumnDefinition

# A schema definition collected by ``Blueprint`` and compiled by ``Schema``.
type SchemaDefinition = (
    ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique
)
