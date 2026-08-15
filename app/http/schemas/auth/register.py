from orionis.schemas.constraints import Email, MinLength
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message
from orionis.schemas import Schema

class RegisterSchema(Schema):

    name: Field[
        str,
        Message("Name must be a string."),
        MinLength(2, message="Name must be at least 2 characters long."),
    ]

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

    password_confirmation: Field[
        str,
        Message("Password confirmation must be a string."),
        MinLength(8, message="Password confirmation must be at least 8 characters long."),
    ]

