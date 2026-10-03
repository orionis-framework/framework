from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.realtime.clients import HubClients
    from orionis.realtime.decorators import remote
    from orionis.realtime.entities import BroadcastResult
    from orionis.realtime.groups import HubGroups
    from orionis.realtime.hub import Hub, HubContext
    from orionis.realtime.manager import ConnectionManager
    from orionis.realtime.protocol import HubProtocol

__all__ = [
    "BroadcastResult", "ConnectionManager", "Hub", "HubClients", "HubContext",
    "HubGroups", "HubProtocol", "remote",
]

_EXPORTS = {
    "BroadcastResult": ("orionis.realtime.entities", "BroadcastResult"),
    "ConnectionManager": ("orionis.realtime.manager", "ConnectionManager"),
    "Hub": ("orionis.realtime.hub", "Hub"),
    "HubClients": ("orionis.realtime.clients", "HubClients"),
    "HubContext": ("orionis.realtime.hub", "HubContext"),
    "HubGroups": ("orionis.realtime.groups", "HubGroups"),
    "HubProtocol": ("orionis.realtime.protocol", "HubProtocol"),
    "remote": ("orionis.realtime.decorators", "remote"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a declared realtime export.

    Parameters
    ----------
    name : str
        Public package attribute requested by application code.

    Returns
    -------
    object
        Declared realtime class or decorator.

    Raises
    ------
    AttributeError
        If the name is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """List declared exports and loaded package attributes.

    Returns
    -------
    list[str]
        Sorted public and loaded names.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
