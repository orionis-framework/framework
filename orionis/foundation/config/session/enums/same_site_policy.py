from enum import Enum

class SameSitePolicy(Enum):
    """
    Represent possible values for the SameSite attribute of cookies.

    Attributes
    ----------
    LAX : str
        Cookies are withheld on cross-site subrequests, but sent when a user
        navigates to the URL from an external site (e.g., following a link).
    STRICT : str
        Cookies are only sent in a first-party context and not with requests
        initiated by third party websites.
    NONE : str
        Cookies are sent in all contexts, i.e., in responses to both first-party
        and cross-origin requests.

    Returns
    -------
    SameSitePolicy
        An enumeration member representing the SameSite policy.
    """

    LAX = "lax"
    STRICT = "strict"
    NONE = "none"
