from enum import StrEnum

class MailDriver(StrEnum):
    """
    Enumeration of supported mail drivers.

    Attributes
    ----------
    SMTP : str
        Simple Mail Transfer Protocol driver.
    FILE : str
        File-based driver.
    """

    SMTP = "smtp"
    FILE = "file"
