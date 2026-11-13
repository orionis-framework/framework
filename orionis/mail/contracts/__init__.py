"""Group the mail contracts components and public imports."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.mail.contracts.manager import IMailManager
    from orionis.mail.contracts.transport import IMailTransport

__all__ = [
    "IMailManager",
    "IMailTransport",
]

_EXPORTS = {
    "IMailManager": ("orionis.mail.contracts.manager", "IMailManager"),
    "IMailTransport": ("orionis.mail.contracts.transport", "IMailTransport"),
}
"""Public contract names mapped to their defining modules and attributes."""


def __getattr__(name: str) -> object:
    """Resolve and cache a public contract without importing unrelated services.

    Parameters
    ----------
    name : str
        Contract requested from this package.

    Returns
    -------
    object
        Original contract from its defining module.

    Raises
    ------
    AttributeError
        If the requested name is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """List loaded attributes and declared public contracts.

    Returns
    -------
    list[str]
        Sorted attribute names available from this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
