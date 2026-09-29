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
        Async callable that reads the previously submitted form input.
    """
    async def old(key: str, default: Any = None) -> Any:
        """
        Return the value submitted for *key* in the previous request.

        Reads the payload flashed with ``withInput()``.  Status messages
        and validation errors are **not** reachable here; use the
        ``flash()`` and ``errors`` globals instead.

        Parameters
        ----------
        key : str
            Form field name.
        default : Any, optional
            Fallback value when the field was not submitted.

        Returns
        -------
        Any
            The previously submitted value, ``default``, or an empty
            string when both are ``None``.
        """
        try:
            session: ISession = await app.make(ISession)
        except Exception:
            value: Any = default
        else:
            value = session.getOldInput(key, default)

        return "" if value is None else value

    return old
