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
    HTTP : Runtime
        Represents the HTTP runtime environment.
    CLI : Runtime
        Represents the CLI runtime environment.

    Returns
    -------
    Runtime
        Enumeration member representing a runtime environment.
    """

    HTTP = "http"
    CLI = "cli"
