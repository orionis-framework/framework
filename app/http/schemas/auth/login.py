from orionis.schemas.constraints import Email, MinLength
from orionis.schemas.fields import Field, Nullable
from orionis.schemas.metadata import Message
from orionis.schemas import Schema

class LoginSchema(Schema):

    email: Field[
        str,
        Message("Email must be a string."),
        MinLength(5, message="Email must be at least 5 characters long."),
        Email(message="Email must be a valid email address."),
    ]

    password: Field[
        str,
        Message("Password must be a string."),
        MinLength(8, message="Password must be at least 8 characters long."),
    ]

    remember: Nullable[str] = None
