"""Provide view globals operations through ``_global_session``."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.session.contracts.session import ISession

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401, BLE001

def _global_session(app: IApplication) -> Any:
    """
    Build the async ``session`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    typing.Any
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
            from orionis.view._failures import capture_service_failure  # noqa: PLC0415
            await capture_service_failure(error, ISession, app=app)
            return None

    return session
