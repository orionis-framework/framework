from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.http.contracts.request import IRequest

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401, BLE001

def _global_request(app: IApplication) -> Any:
    """
    Build the async ``request`` template global.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
        Async callable that resolves the current HTTP request.
    """
    async def request() -> IRequest | None:
        """
        Resolve the current HTTP request from the container.

        Returns
        -------
        IRequest | None
            The HTTP request bound to the active request scope, or
            ``None`` when no request is in scope.
        """
        try:
            return await app.make(IRequest)
        except Exception:
            return None

    return request
