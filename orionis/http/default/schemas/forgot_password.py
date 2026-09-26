from orionis.schemas import Schema
from orionis.schemas.constraints import Email, MaxLength
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message

class ForgotPasswordSchema(Schema):

    # ruff: noqa: TC001 (Runtime schema metadata)

    email: Field[
        str,
        Message("Enter a valid email address."),
        MaxLength(255),
        Email(message="Enter a valid email address."),
    ]
