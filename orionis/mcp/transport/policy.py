from http import HTTPStatus
import logging
from typing import TYPE_CHECKING, ClassVar
from orionis.auth.exceptions import AuthenticationException, AuthorizationException
from orionis.foundation.contracts.application import IApplication  # noqa: TC001 - Native DI.
from orionis.http.adapters.response.streams import close_stream
from orionis.http.contracts.endpoint_policy import IHttpEndpointPolicy
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.payload.body import PayloadTooLargeException
from orionis.http.request import UnsupportedMediaTypeException
from orionis.http.responses import EventStreamResponse, Response
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.mcp.config import McpConfig  # noqa: TC001 - Native DI.
from orionis.mcp.exceptions import McpProtocolException
from orionis.mcp.protocol.codecs import encode_error
from orionis.schemas.exceptions.validation import ValidationException

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.payload.estructures.headers import Headers
    from orionis.http.request import Request

_REDIRECTION_START = 300
_CLIENT_ERROR_START = 400
_SERVER_ERROR_START = 500
_JSON_MEDIA_TYPE = "application/json"
_REPLACED_HEADERS = frozenset({"content-type", "content-length", "location"})
_AUTHENTICATION_HEADERS = frozenset({"www-authenticate", "allow"})
_LOGGER = logging.getLogger(__name__)
_EXCEPTION_STATUS = {
    AuthenticationException: HTTPStatus.UNAUTHORIZED,
    AuthorizationException: HTTPStatus.FORBIDDEN,
    RouteNotFound: HTTPStatus.NOT_FOUND,
    MethodNotAllowed: HTTPStatus.METHOD_NOT_ALLOWED,
    PayloadTooLargeException: HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    UnsupportedMediaTypeException: HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
    CSRFTokenMismatchException: HTTPStatus.FORBIDDEN,
    ValidationException: HTTPStatus.UNPROCESSABLE_ENTITY,
}

class McpProtocolResponse(Response):
    """Mark encoded protocol output to keep adaptation constant-time."""

    __slots__ = ()

    def __init__(
        self, content: bytes, status_code: int = 200,
        headers: Mapping[str, str] | None = None, media_type: str = _JSON_MEDIA_TYPE,
    ) -> None:
        """
        Keep preencoded bytes while emitting mandatory JSON response metadata.

        Parameters
        ----------
        content : bytes
            Value supplied for ``content``.
        status_code : int
            Value supplied for ``status_code``.
        headers : Mapping[str, str] | None
            Value supplied for ``headers``.
        media_type : str
            Value supplied for ``media_type``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        super().__init__(
            content=content, status_code=status_code, headers=headers,
            media_type=media_type,
        )
        self.setHeader("Content-Type", _JSON_MEDIA_TYPE)
        self.setHeader("Content-Length", str(len(content)))

def origin_allowed(headers: Headers, origins: frozenset[str]) -> bool:
    """
    Accept absent origins and one explicitly configured serialized origin.

    Parameters
    ----------
    headers : Headers
        Value supplied for ``headers``.
    origins : frozenset[str]
        Value supplied for ``origins``.

    Returns
    -------
    bool
        Result of the operation described above.
    """
    count = headers.count("origin")
    return count == 0 or (count == 1 and headers.get("origin") in origins)

def _error(status: int) -> McpProtocolResponse:
    """
    Use public status names rather than exception messages or middleware bodies.

    Parameters
    ----------
    status : int
        Value supplied for ``status``.

    Returns
    -------
    McpProtocolResponse
        Result of the operation described above.
    """
    try:
        message = HTTPStatus(status).phrase
    except ValueError:
        message = "Request failed"
    exception = McpProtocolException(
        -32603 if status >= _SERVER_ERROR_START else -32600,
        message, status=status,
    )
    response = McpProtocolResponse(
        content=encode_error(exception), status_code=status,
        media_type=_JSON_MEDIA_TYPE,
    )
    if status == HTTPStatus.METHOD_NOT_ALLOWED:
        response.setHeader("Allow", "POST")
    if status == HTTPStatus.UNAUTHORIZED:
        response.setHeader("WWW-Authenticate", "Bearer")
    return response

class McpHttpPolicy(IHttpEndpointPolicy):
    """Enforce MCP origin and error rules around the existing HTTP pipeline."""

    __slots__ = ("_app", "_origins")
    monitor_disconnects: ClassVar[bool] = True

    def __init__(self, app: IApplication, config: McpConfig) -> None:
        """
        Compile an origin set without capturing any request or identity.

        Parameters
        ----------
        app : IApplication
            Application container supplying configuration and dependencies.
        config : McpConfig
            Validated configuration controlling this component.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._app = app
        self._origins = frozenset(config.allowed_origins)

    def before(self, adapter: TransportAdapter) -> Response | None:
        """
        Validate Origin for preflight and unsupported methods as well as POST.

        Parameters
        ----------
        adapter : TransportAdapter
            Value supplied for ``adapter``.

        Returns
        -------
        Response | None
            Result of the operation described above.
        """
        return None if origin_allowed(adapter.headers(), self._origins) else _error(403)

    async def response(self, response: Response) -> Response:
        """
        Preserve protocol output and replace browser bodies with safe errors.

        Parameters
        ----------
        response : Response
            Value supplied for ``response``.

        Returns
        -------
        Response
            Result of the operation described above.
        """
        if isinstance(response, McpProtocolResponse):
            return response
        status = response.getStatusCode()
        if status < _REDIRECTION_START and (
            isinstance(response, EventStreamResponse) or not response.getBody()
        ):
            return response
        status = status if status >= _CLIENT_ERROR_START else HTTPStatus.FORBIDDEN
        replacement = _error(status)
        replaced: set[str] = set()
        for name, value in response.getStringHeaders():
            key = name.lower()
            if key not in _REPLACED_HEADERS:
                if key in _AUTHENTICATION_HEADERS and key not in replaced:
                    replacement.removeHeader(name)
                    replaced.add(key)
                replacement.addHeader(name, value)
        await close_stream(response.getStream(), None)
        return replacement

    async def exception(
        self, exception: Exception, request: Request | TransportAdapter,
    ) -> Response:
        """
        Report failures without calling the native HTML/debug presenter.

        Parameters
        ----------
        exception : Exception
            Exception being inspected or reported.
        request : Request | TransportAdapter
            Current request and its trusted execution context.

        Returns
        -------
        Response
            Result of the operation described above.
        """
        del request
        try:
            handler = await self._app.getExceptionHandler()
            await self._app.call(handler, "report", exception=exception)
        except Exception:
            _LOGGER.exception("MCP failure reporting could not complete")
        if isinstance(exception, McpProtocolException):
            return McpProtocolResponse(
                content=encode_error(exception), status_code=exception.status,
                media_type=_JSON_MEDIA_TYPE,
            )
        for ancestor in type(exception).__mro__:
            status = _EXCEPTION_STATUS.get(ancestor)
            if status is not None:
                return _error(status)
        return _error(HTTPStatus.INTERNAL_SERVER_ERROR)
