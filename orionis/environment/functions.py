from __future__ import annotations
from orionis.environment.facade import Env

def env(key: str, default: object | None = None) -> object:
    """
    Retrieve the value of an environment variable using the Env facade.

    Parameters
    ----------
    key : str
        The name of the environment variable to retrieve.
    default : object | None, optional
        The value to return if the environment variable is not found.
        Defaults to None.

    Returns
    -------
    object
        The value of the environment variable if it exists, otherwise the
        specified default value.
    """
    # Retrieve the environment variable using the Env singleton instance
    return Env.get(key, default)
