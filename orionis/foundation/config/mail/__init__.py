from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.mail.entities.file import File
    from orionis.foundation.config.mail.entities.from_address import FromAddress
    from orionis.foundation.config.mail.entities.mail import Mail
    from orionis.foundation.config.mail.entities.mailers import Mailers
    from orionis.foundation.config.mail.entities.smtp import Smtp
    from orionis.foundation.config.mail.enums.drivers import MailDriver

__all__ = [
    "File",
    "FromAddress",
    "Mail",
    "MailDriver",
    "Mailers",
    "Smtp",
]

_EXPORTS = {
    "File": ("orionis.foundation.config.mail.entities.file", "File"),
    "FromAddress": ("orionis.foundation.config.mail.entities.from_address", "FromAddress"),
    "Mail": ("orionis.foundation.config.mail.entities.mail", "Mail"),
    "MailDriver": ("orionis.foundation.config.mail.enums.drivers", "MailDriver"),
    "Mailers": ("orionis.foundation.config.mail.entities.mailers", "Mailers"),
    "Smtp": ("orionis.foundation.config.mail.entities.smtp", "Smtp"),
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
