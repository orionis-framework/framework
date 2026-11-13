# ruff: noqa: TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
"""Provide view globals operations.

Includes ``_global_csrf_token``, ``_global_csrf_field``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from markupsafe import Markup

from orionis.foundation.contracts.application import IApplication
from orionis.session.contracts.session import ISession

_CSRF_SESSION_KEY = "_csrf_token"
"""Csrf session key identifier: ``_csrf_token``."""

# Form field read back by ``CSRFTokenMiddleware`` on unsafe requests.
_CSRF_FIELD_NAME = "_csrf"
"""Form field read back by ``CSRFTokenMiddleware`` on unsafe requests."""

# Template of the hidden input; ``Markup.format`` escapes the token.
_CSRF_FIELD_TEMPLATE = Markup(
    '<input type="hidden" name="{name}" value="{token}">',
)
"""Template of the hidden input; ``Markup.format`` escapes the token."""


def _global_csrf_token(app: IApplication) -> Callable[[], Awaitable[str]]:
    """
    Build the async ``csrf_token`` template global bound to the application.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
        Async callable that reads the CSRF token from the session.
    """
    # Resolve the session key once: configuration is frozen after boot.
    key: str = app.config("http.csrf.session_key") or _CSRF_SESSION_KEY

    async def csrf_token() -> str:
        """
        Return the CSRF token stored in the current session.

        The token is written by ``CSRFTokenMiddleware`` under the key
        declared in ``http.csrf.session_key``.

        Returns
        -------
        str
            The token from the active session, or an empty string when no
            token has been issued. Service-resolution errors propagate.
        """
        session: ISession = await app.make(ISession)
        return session.get(key) or ""

    return csrf_token


def _global_csrf_field(app: IApplication) -> Callable[[], Awaitable[Markup]]:
    """
    Build the async ``csrf_field`` template global bound to the application.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
        Async callable that returns a hidden input field with the CSRF token.
    """
    read_token = _global_csrf_token(app)

    async def csrf_field() -> Markup:
        """
        Return a hidden input field with the CSRF token.

        Returns
        -------
        ``markupsafe.Markup``
            Safe HTML markup with the hidden input, exempt from the
            environment autoescaping so templates need no ``| safe``.
        """
        token: str = await read_token()
        return _CSRF_FIELD_TEMPLATE.format(
            name=_CSRF_FIELD_NAME,
            token=token,
        )

    return csrf_field
