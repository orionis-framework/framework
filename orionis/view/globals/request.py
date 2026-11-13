# ruff: noqa: BLE001, TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
# Observe optional service failures centrally before returning a fallback.
"""Provide view globals operations through ``_global_request``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from orionis.foundation.contracts.application import IApplication
from orionis.http.contracts.request import IRequest
from orionis.view._failures import capture_service_failure


def _global_request(app: IApplication) -> Callable[[], Awaitable[IRequest | None]]:
    """
    Build the async ``request`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
        Async callable that resolves the current HTTP request.
    """

    async def request() -> IRequest | None:
        """
        Resolve the current HTTP request from the container.

        Returns
        -------
        orionis.http.contracts.request.IRequest | None
            The HTTP request bound to the active request scope, or
            ``None`` when no request is in scope.
        """
        try:
            return await app.make(IRequest)
        except Exception as error:
            await capture_service_failure(error, IRequest, app=app)
            return None

    return request
