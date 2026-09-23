from enum import StrEnum

class MailEncryption(StrEnum):
    """
    Enumerate the transport security modes accepted by the SMTP driver.

    Members inherit from :class:`str`, so a configuration value and an
    enumeration member are interchangeable once normalized. Configured
    names are matched without case sensitivity.

    Attributes
    ----------
    TLS : str
        Mandatory STARTTLS upgrade over a plain connection.
    SSL : str
        Implicit TLS negotiated before the SMTP greeting.
    NONE : str
        Explicitly requested plaintext connection.
    """

    TLS = "tls"
    SSL = "ssl"
    NONE = "none"
