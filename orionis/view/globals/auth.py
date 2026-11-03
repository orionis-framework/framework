"""Provide view globals operations through ``_global_auth``."""

from typing import TYPE_CHECKING
from orionis.support.facades import Auth

if TYPE_CHECKING:
    from collections.abc import Callable

def _global_auth() -> Callable[[], type[Auth]]:
    """
    Build the ``auth`` template global.

    Returns
    -------
    collections.abc.Callable[[], type[orionis.support.facades.Auth]]
        Callable exposing the authentication facade without caching a user.
    """
    def auth() -> type[Auth]:
        """
        Return the authentication facade for the active request.

        Returns
        -------
        type[orionis.support.facades.Auth]
            Facade exposing the current request's authentication context.
        """
        return Auth

    return auth
