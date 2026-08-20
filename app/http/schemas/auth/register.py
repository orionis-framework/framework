from orionis.schemas.constraints import ConfirmPassword, Email, MinLength, Unique
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message
from orionis.schemas import Schema

class RegisterSchema(Schema):

    name: Field[
        str,
        Message("Name must be a string."),
        MinLength(6, message="Name must be at least 6 characters long."),
    ]

    email: Field[
        str,
        Message("Email must be a string."),
        Email(message="Email must be a valid email address."),
        Unique(
            table="users",
            column="email",
            message="Email already exists. Please use a different email address.",
        ),
    ]

    password: Field[
        str,
        Message("Password must be a string."),
        MinLength(8, message="Password must be at least 8 characters long."),
    ]

    password_confirmation: Field[
        str,
        Message("Password confirmation must be a string."),
        ConfirmPassword(message="Password confirmation does not match the password."),
    ]
