from orionis.schemas import Schema
from orionis.schemas.constraints import (
    ConfirmPassword, MaxLength, MinLength, StrongPassword,
)
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message

class ChangePasswordSchema(Schema):
    """
    Validate password changes with the existing credential field names.

    Attributes
    ----------
    current_password : str
        Current account password submitted for verification.
    password : str
        New password that satisfies the strength requirements.
    password_confirmation : str
        Confirmation matching the new password.

    Returns
    -------
    ChangePasswordSchema
        Validated password-change payload with normalized string fields.
    """

    # Declare the current password validation rules.
    current_password: Field[
        str,
        Message("Enter your current password."),
        MinLength(1, message="Enter your current password."),
        MaxLength(1024, message="Password must not exceed 1024 characters."),
    ]

    # Declare the new password validation rules.
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

    # Declare the password confirmation validation rules.
    password_confirmation: Field[
        str,
        Message("Confirm your new password."),
        MinLength(1, message="Confirm your new password."),
        MaxLength(1024, message="Password must not exceed 1024 characters."),
        ConfirmPassword(message="Password confirmation does not match."),
    ]
