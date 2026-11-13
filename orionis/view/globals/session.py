# ruff: noqa: BLE001, TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
# Observe optional service failures centrally before returning a fallback.
"""Provide view globals operations through ``_global_session``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from orionis.foundation.contracts.application import IApplication
from orionis.session.contracts.session import ISession
from orionis.view._failures import capture_service_failure


def _global_session(app: IApplication) -> Callable[[], Awaitable[ISession | None]]:
    """
    Build the async ``session`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
        Async callable that resolves the current session.
    """

    async def session() -> ISession | None:
        """
        Resolve the current session from the container.

        Returns
        -------
        orionis.session.contracts.ISession | None
            The session instance bound to the active request scope, or
            ``None`` when the session service is unavailable.
        """
        try:
            return await app.make(ISession)
        except Exception as error:
            await capture_service_failure(error, ISession, app=app)
            return None

    return session
