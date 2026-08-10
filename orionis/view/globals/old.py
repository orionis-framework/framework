from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.session.contracts.session import ISession

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401, BLE001

def _global_old(app: IApplication) -> Any:
    """
    Build the async ``old`` template global.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
        Async callable that reads flashed values from the session.
    """
    async def old(key: str, default: Any = None) -> Any:
        """
        Return a value flashed during the previous request.

        Parameters
        ----------
        key : str
            Flash data key, as passed to ``Response.withFlash()``.
        default : Any, optional
            Fallback value when the key is absent or no session exists.

        Returns
        -------
        Any
            The flashed value, or *default*.
        """
        try:
            session: ISession = await app.make(ISession)
        except Exception:
            return default

        return session.getFlash(key, default)

    return old
