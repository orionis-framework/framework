from typing import ClassVar
from database.schemas.users_v1 import USERS_V1
from orionis.auth import Authenticatable, Authorizable, MustVerifyEmail
from orionis.orm import Model
from orionis.orm.schema.table import TableDefinition

class User(Model, Authenticatable, Authorizable, MustVerifyEmail):

    # Database table associated with the User model.
    table_definition: TableDefinition = USERS_V1

    # Attribute type casting applied when reading/hydrating model values.
    casts: ClassVar[dict[str, str]] = {
        "active": "bool",
        "email_verified_at": "datetime",
    }

    # Attributes excluded from the serialized output (toDict()/JSON).
    hidden: ClassVar[list[str]] = ["password", "remember_token"]

    # Attributes allowed for mass assignment.
    fillable: ClassVar[list[str]] = ["name", "email", "password", "active"]
