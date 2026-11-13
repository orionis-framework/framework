# ruff: noqa: S105
# Keep the existing boundary behavior and deliberately shaped fixtures.
"""Enumerate the authentication guards shipped with the framework."""

from enum import StrEnum


class Guards(StrEnum):
    """
    Enumerate the authentication guards shipped with the framework.

    Attributes
    ----------
    SESSION : str
        Guard resolving the identity from the HTTP session.
    TOKEN : str
        Guard resolving the identity from a personal access token.

    Returns
    -------
    orionis.foundation.config.auth.enums.Guards
        An enumeration member representing an authentication guard.
    """

    SESSION = "session"
    TOKEN = "token"
