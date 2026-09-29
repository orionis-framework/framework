from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.session.contracts.session import ISession

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401, BLE001

def _global_flash(app: IApplication) -> Any:
    """
    Build the async ``flash`` template global.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
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

    return flash
