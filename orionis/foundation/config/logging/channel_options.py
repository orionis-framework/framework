from __future__ import annotations
from typing import cast
from orionis.environment import Env

def channel_option[T](channel: str, key: str, default: T) -> T:
    """
    Read a shared logging option for the selected channel.

    Parameters
    ----------
    channel : str
        Channel owning the environment override.
    key : str
        Environment variable containing the override.
    default : T
        Value returned for other channels or an unset variable.

    Returns
    -------
    T
        Selected channel's override or its default value.
    """
    if Env.get("LOG_CHANNEL", "stack") != channel:
        return default
    return cast("T", Env.get(key, default))
