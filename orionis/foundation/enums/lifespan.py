from enum import StrEnum

class Lifespan(StrEnum):
    """
    Define the possible lifespan events for the application.

    Attributes
    ----------
    STARTUP : str
        Indicates the startup event of the application.
    SHUTDOWN : str
        Indicates the shutdown event of the application.
    """

    STARTUP = "lifespan.startup"
    SHUTDOWN = "lifespan.shutdown"
