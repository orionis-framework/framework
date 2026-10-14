from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.mail.transports.file import FileTransport, create_file_transport
    from orionis.mail.transports.smtp import SmtpTransport, create_smtp_transport

__all__ = [
    "FileTransport",
    "SmtpTransport",
    "create_file_transport",
    "create_smtp_transport",
]

_EXPORTS = {
    "FileTransport": ("orionis.mail.transports.file", "FileTransport"),
    "SmtpTransport": ("orionis.mail.transports.smtp", "SmtpTransport"),
    "create_file_transport": ("orionis.mail.transports.file", "create_file_transport"),
    "create_smtp_transport": ("orionis.mail.transports.smtp", "create_smtp_transport"),
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
