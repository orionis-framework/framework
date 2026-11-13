# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Validate sign-in credentials and the remember-session option."""

from orionis.schemas import Schema
from orionis.schemas.constraints import Email, MinLength
from orionis.schemas.fields import Field, Nullable
from orionis.schemas.metadata import Message


class LoginSchema(Schema):
    """Validate sign-in credentials and the remember-session option."""

    email: Field[
        str,
        Message("Email must be a string."),
        MinLength(5, message="Email must be at least 5 characters long."),
        Email(message="Email must be a valid email address."),
    ]
    """Email address subject to the declared length and address constraints."""

    password: Field[
        str,
        Message("Password must be a string."),
        MinLength(8, message="Password must be at least 8 characters long."),
    ]
    """Account password subject to the declared validation constraints."""

    remember: Nullable[str] = None
    """Optional request value enabling persistent authentication."""
