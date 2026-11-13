# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Validate password-reset credentials and the replacement password."""

from orionis.http.default.schemas.forgot_password import ForgotPasswordSchema
from orionis.schemas.constraints import (
    ConfirmPassword,
    MaxLength,
    MinLength,
    Pattern,
    StrongPassword,
)
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message


class ResetPasswordSchema(ForgotPasswordSchema):
    # (Runtime schema metadata)
    """Validate password-reset credentials and the replacement password."""

    token: Field[
        str,
        MinLength(43),
        MaxLength(43),
        Pattern(r"^[A-Za-z0-9_-]{43}$"),
    ]
    """Token identifying the current reservation or protected operation."""
    password: Field[
        str,
        Message("Enter a new password."),
        MinLength(8),
        MaxLength(1024),
        StrongPassword(
            message=(
                "Use at least 8 characters, an uppercase letter, "
                "a lowercase letter and a number."
            ),
        ),
    ]
    """Account password subject to the declared validation constraints."""
    password_confirmation: Field[
        str,
        Message("Confirm your new password."),
        MinLength(1),
        MaxLength(1024),
        ConfirmPassword(message="Password confirmation does not match."),
    ]
    """Repeated password value that must match the password field."""
