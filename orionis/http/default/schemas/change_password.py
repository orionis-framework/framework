from orionis.schemas import Schema
from orionis.schemas.constraints import (
    ConfirmPassword, MaxLength, MinLength, StrongPassword,
)
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message

class ChangePasswordSchema(Schema):

    # ruff: noqa: TC001 (Runtime schema metadata)

    current_password: Field[
        str,
        Message("Enter your current password."),
        MinLength(1, message="Enter your current password."),
        MaxLength(1024, message="Password must not exceed 1024 characters."),
    ]

    password: Field[
        str,
        Message("Enter a new password."),
        MinLength(8, message="Password must be at least 8 characters long."),
        MaxLength(1024, message="Password must not exceed 1024 characters."),
        StrongPassword(message=(
            "Use at least 8 characters, an uppercase letter, "
            "a lowercase letter and a number."
        )),
    ]

    password_confirmation: Field[
        str,
        Message("Confirm your new password."),
        MinLength(1, message="Confirm your new password."),
        MaxLength(1024, message="Password must not exceed 1024 characters."),
        ConfirmPassword(message="Password confirmation does not match."),
    ]
