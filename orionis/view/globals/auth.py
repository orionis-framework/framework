from typing import TYPE_CHECKING
from orionis.support.facades import Auth

if TYPE_CHECKING:
    from collections.abc import Callable

def _global_auth() -> Callable[[], type[Auth]]:
    """
    Build the ``auth`` template global.

    Returns
    -------
    Callable[[], type[Auth]]
        Callable exposing the authentication facade without caching a user.
    """
    def auth() -> type[Auth]:
        """
        Return the authentication facade for the active request.

        Returns
        -------
        type[Auth]
            Facade exposing the current request's authentication context.
        """
        return Auth

    return auth
