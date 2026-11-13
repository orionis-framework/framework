# ruff: noqa: ANN401, BLE001, TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
# Preserve heterogeneous template payload values.
# Observe optional service failures centrally before returning a fallback.
"""Provide view globals operations through ``_global_old``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from orionis.foundation.contracts.application import IApplication
from orionis.session.contracts.session import ISession
from orionis.view._failures import capture_service_failure


def _global_old(app: IApplication) -> Callable[..., Awaitable[Any]]:
    """
    Build the async ``old`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
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
        default : typing.Any, optional
            Fallback value when the field was not submitted.

        Returns
        -------
        typing.Any
            The previously submitted value, ``default``, or an empty
            string when both are ``None``.
        """
        try:
            session: ISession = await app.make(ISession)
        except Exception as error:
            await capture_service_failure(error, ISession, app=app)
            value: Any = default
        else:
            value = session.getOldInput(key, default)

        return "" if value is None else value

    return old
