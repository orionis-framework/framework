from enum import Enum

class Environments(Enum):
    """
    Enumerate possible application environments.

    Attributes
    ----------
    DEVELOPMENT : str
        Represents the development environment.
    TESTING : str
        Represents the testing environment.
    PRODUCTION : str
        Represents the production environment.

    Returns
    -------
    Environments
        The enumeration member representing the environment.
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
