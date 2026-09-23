from enum import StrEnum

class MailStatus(StrEnum):
    """
    Enumerate the outcomes a transport can confirm for one operation.

    Members inherit from :class:`str`, so they compare equal to the plain
    status strings exposed in results and serialized payloads. No member
    confirms mailbox delivery or that a recipient read the message.

    Attributes
    ----------
    ACCEPTED : str
        SMTP accepted the message for every intended recipient.
    PARTIAL : str
        SMTP accepted the message for some recipients and rejected others.
    STORED : str
        The file transport published the complete message on disk.
    """

    ACCEPTED = "accepted"
    PARTIAL = "partial"
    STORED = "stored"
