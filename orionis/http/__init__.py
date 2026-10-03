from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.http.factory import ResponseFactory, response
    from orionis.http.middleware import (
        BaseMiddleware,
        NextCallable,
    )
    from orionis.http.request import Request
    from orionis.http.responses import (
        FileResponse,
        HTMLResponse,
        JSONResponse,
        PlainTextResponse,
        RedirectResponse,
        Response,
        ResponseTemplate,
        StreamingResponse,
    )
    from orionis.http.types import HttpResponse
    from orionis.http.websocket import WebSocket, WebSocketDisconnected
    from orionis.http.websocket_middleware import WebSocketMiddleware, WebSocketNext

__all__ = [
    "BaseMiddleware",
    "FileResponse",
    "HTMLResponse",
    "HttpResponse",
    "JSONResponse",
    "NextCallable",
    "PlainTextResponse",
    "RedirectResponse",
    "Request",
    "Response",
    "ResponseFactory",
    "ResponseTemplate",
    "StreamingResponse",
    "WebSocket",
    "WebSocketDisconnected",
    "WebSocketMiddleware",
    "WebSocketNext",
    "response",
]

_EXPORTS = {
    "BaseMiddleware": ("orionis.http.middleware", "BaseMiddleware"),
    "FileResponse": ("orionis.http.responses", "FileResponse"), # NOSONAR
    "HTMLResponse": ("orionis.http.responses", "HTMLResponse"),
    "HttpResponse": ("orionis.http.types", "HttpResponse"),
    "JSONResponse": ("orionis.http.responses", "JSONResponse"),
    "NextCallable": ("orionis.http.middleware", "NextCallable"),
    "PlainTextResponse": ("orionis.http.responses", "PlainTextResponse"),
    "RedirectResponse": ("orionis.http.responses", "RedirectResponse"),
    "Request": ("orionis.http.request", "Request"),
    "Response": ("orionis.http.responses", "Response"),
    "ResponseFactory": ("orionis.http.factory", "ResponseFactory"),
    "ResponseTemplate": ("orionis.http.responses", "ResponseTemplate"),
    "StreamingResponse": ("orionis.http.responses", "StreamingResponse"),
    "WebSocket": ("orionis.http.websocket", "WebSocket"),
    "WebSocketDisconnected": ("orionis.http.websocket", "WebSocketDisconnected"),
    "WebSocketMiddleware": (
        "orionis.http.websocket_middleware", "WebSocketMiddleware",
    ),
    "WebSocketNext": ("orionis.http.websocket_middleware", "WebSocketNext"),
    "response": ("orionis.http.factory", "response"),
}

def __getattr__(name: str) -> object:
    """Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
