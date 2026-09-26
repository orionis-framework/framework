from orionis.http.default.schemas.forgot_password import ForgotPasswordSchema
from orionis.schemas.constraints import (
    ConfirmPassword, MaxLength, MinLength, Pattern, StrongPassword,
)
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message


class ResetPasswordSchema(ForgotPasswordSchema):
    """Apply the application's password policy and confirmation to a reset."""

    # ruff: noqa: TC001 (Runtime schema metadata)

    token: Field[
        str, MinLength(43), MaxLength(43), Pattern(r"^[A-Za-z0-9_-]{43}$"),
    ]
    password: Field[
        str,
        Message("Enter a new password."),
        MinLength(8),
        MaxLength(1024),
        StrongPassword(message=(
            "Use at least 8 characters, an uppercase letter, "
            "a lowercase letter and a number."
        )),
    ]
    password_confirmation: Field[
        str,
        Message("Confirm your new password."),
        MinLength(1),
        MaxLength(1024),
        ConfirmPassword(message="Password confirmation does not match."),
    ]
