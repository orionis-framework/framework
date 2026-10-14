from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.mail.entities.address import Address
    from orionis.mail.entities.attachment import Attachment
    from orionis.mail.entities.content import Content
    from orionis.mail.entities.envelope import Envelope
    from orionis.mail.entities.result import MailResult
    from orionis.mail.enums.status import MailStatus
    from orionis.mail.mailable import Mailable
    from orionis.mail.message import Message
    from orionis.mail.pending import PendingMail

__all__ = [
    "Address",
    "Attachment",
    "Content",
    "Envelope",
    "MailResult",
    "MailStatus",
    "Mailable",
    "Message",
    "PendingMail",
]

_EXPORTS = {
    "Address": ("orionis.mail.entities.address", "Address"),
    "Attachment": ("orionis.mail.entities.attachment", "Attachment"),
    "Content": ("orionis.mail.entities.content", "Content"),
    "Envelope": ("orionis.mail.entities.envelope", "Envelope"),
    "MailResult": ("orionis.mail.entities.result", "MailResult"),
    "MailStatus": ("orionis.mail.enums.status", "MailStatus"),
    "Mailable": ("orionis.mail.mailable", "Mailable"),
    "Message": ("orionis.mail.message", "Message"),
    "PendingMail": ("orionis.mail.pending", "PendingMail"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
