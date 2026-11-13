"""Define runtime environments for the framework."""

from enum import StrEnum


class Runtime(StrEnum):
    """
    Define runtime environments for the framework.

    Notes
    -----
    This enumeration specifies the available runtime environments for the
    framework.

    Attributes
    ----------
    HTTP : orionis.foundation.enums.Runtime
        Represents the HTTP runtime environment.
    CLI : orionis.foundation.enums.Runtime
        Represents the CLI runtime environment.

    Returns
    -------
    orionis.foundation.enums.Runtime
        Enumeration member representing a runtime environment.
    """

    HTTP = "http"
    CLI = "cli"
