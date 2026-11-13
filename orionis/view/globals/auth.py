# ruff: noqa: TC003
# Keep public callback and application annotations resolvable at runtime.
"""Provide view globals operations through ``_global_auth``."""

from collections.abc import Callable

from orionis.support.facades import Auth


def _global_auth() -> Callable[[], type[Auth]]:
    """
    Build the ``auth`` template global.

    Returns
    -------
    collections.abc.Callable
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
