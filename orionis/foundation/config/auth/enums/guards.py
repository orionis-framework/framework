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
    Guards
        An enumeration member representing an authentication guard.
    """

    SESSION = "session"
    TOKEN = "token"  # noqa: S105
