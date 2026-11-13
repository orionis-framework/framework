# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Validate the email address used to request a password reset."""

from orionis.schemas import Schema
from orionis.schemas.constraints import Email, MaxLength
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Message


class ForgotPasswordSchema(Schema):
    # (Runtime schema metadata)
    """Validate the email address used to request a password reset."""

    email: Field[
        str,
        Message("Enter a valid email address."),
        MaxLength(255),
        Email(message="Enter a valid email address."),
    ]
    """Email address subject to the declared length and address constraints."""
