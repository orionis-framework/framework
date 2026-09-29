from enum import StrEnum

class Interface(StrEnum):
    """Represent the supported HTTP interface types.

    Attributes
    ----------
    ASGI : str
        Represents the ASGI interface.
    RSGI : str
        Represents the RSGI interface.
    """

    ASGI = "asgi"
    RSGI = "rsgi"
