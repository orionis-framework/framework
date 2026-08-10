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
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
        Async callable that resolves the current session.
    """
    async def session() -> ISession | None:
        """
        Resolve the current session from the container.

        Returns
        -------
        ISession | None
            The session instance bound to the active request scope, or
            ``None`` when the session service is unavailable.
        """
        try:
            return await app.make(ISession)
        except Exception:
            return None

    return session
