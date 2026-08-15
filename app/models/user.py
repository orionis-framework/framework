from typing import ClassVar
from orionis.orm import Model
from orionis.orm import BigInteger, String, DateTime, Boolean

class User(Model):

    # Attribute type casting applied when reading/hydrating model values.
    casts: ClassVar[dict[str, str]] = {
        "active": "bool",
        "email_verified_at": "datetime",
    }

    # Attributes excluded from the serialized output (toDict()/JSON).
    hidden: ClassVar[list[str]] = ["password", "remember_token"]

    # Attributes allowed for mass assignment.
    fillable: ClassVar[list[str]] = ["name", "email", "password"]

    # Attributes
    id = BigInteger().primary().autoIncrement()
    name = String(255)
    email = String(255).unique()
    email_verified_at = DateTime().nullable()
    password = String(255)
    remember_token = String(100).nullable()
    active = Boolean().default(value=True)
    created_at = DateTime().nullable()
    updated_at = DateTime().nullable()
