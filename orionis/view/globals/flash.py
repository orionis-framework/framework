# ruff: noqa: ANN401, BLE001, TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
# Preserve heterogeneous template payload values.
# Observe optional service failures centrally before returning a fallback.
"""Provide view globals operations through ``_global_flash``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from orionis.foundation.contracts.application import IApplication
from orionis.session.contracts.session import ISession
from orionis.view._failures import capture_service_failure


def _global_flash(app: IApplication) -> Callable[..., Awaitable[Any]]:
    """
    Build the async ``flash`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
        Async callable that reads one-request status messages.
    """

    async def flash(key: str, default: Any = None) -> Any:
        """
        Return a status message flashed with ``withFlash()``.

        Values written during the current request are visible immediately,
        so a handler that re-renders its own view reads back what it just
        flashed.

        Parameters
        ----------
        key : str
            Flash data key.
        default : typing.Any, optional
            Fallback value when the key is absent or no session exists.

        Returns
        -------
        typing.Any
            The flashed value, or *default*.
        """
        try:
            session: ISession = await app.make(ISession)
        except Exception as error:
            await capture_service_failure(error, ISession, app=app)
            return default

        return session.getFlash(key, default)

    return flash
