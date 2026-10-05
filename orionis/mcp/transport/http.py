from __future__ import annotations
from http import HTTPStatus
from typing import TYPE_CHECKING, Self
import msgspec
from orionis.http.payload.body import PayloadTooLargeException
from orionis.http.responses import EventStreamResponse, Response
from orionis.http.sse import ServerSentEvent
from orionis.mcp.dispatcher import McpDispatcher
from orionis.mcp.exceptions import McpProtocolException
from orionis.mcp.protocol.codecs import decode_envelope, encode_error
from orionis.mcp.protocol.requests import CallToolParams
from orionis.mcp.streams import AsyncClosable
from orionis.mcp.transport.headers import validate_headers
from orionis.mcp.transport.policy import McpProtocolResponse, origin_allowed

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from orionis.foundation.contracts.application import IApplication
    from orionis.http.payload.estructures.headers import Headers
    from orionis.http.request import Request
    from orionis.mcp.config import McpConfig
    from orionis.mcp.contracts.event_bus import IMcpEventBus
    from orionis.mcp.protocol.requests import JsonRpcRequest, RequestParams
    from orionis.mcp.server.compiler import CompiledMcpServer

_JSON_MEDIA_TYPE = "application/json"
_ACCEPT_MEDIA_TYPES = frozenset({_JSON_MEDIA_TYPE, "text/event-stream"})

class _EventFrames(AsyncClosable):
    """Own an MCP byte iterator even if the HTTP stream is never started."""

    __slots__ = ("_release", "_source")

    def __init__(
        self, source: AsyncIterator[bytes], release: Callable[[], None],
    ) -> None:
        """
        Transfer iterator and admission-slot ownership to the response.

        Parameters
        ----------
        source : AsyncIterator[bytes]
            Source whose values or lifecycle are consumed by this operation.
        release : Callable[[], None]
            Value supplied for ``release``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._source: AsyncIterator[bytes] | None = source
        self._release = release

    def __aiter__(self) -> Self:
        """
        Return this owned, single-use event source.

        Returns
        -------
        Self
            This owned, single-use event source.
        """
        return self

    async def __anext__(self) -> ServerSentEvent:
        """
        Frame one message only when the native HTTP adapter is ready.

        Returns
        -------
        ServerSentEvent
            Result of the operation described above.
        """
        if self._source is None:
            raise StopAsyncIteration
        payload = await anext(self._source)
        return (
            ServerSentEvent(data=payload.decode("utf-8"))
            if payload
            else ServerSentEvent(comment="keepalive")
        )

    async def aclose(self) -> None:
        """
        Close the producer and release admission before scope disposal.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        source, self._source = self._source, None
        if source is None:
            return
        try:
            close = getattr(source, "aclose", None)
            if close is not None:
                await close()
        finally:
            self._release()

def _accept_quality(parameters: str) -> float | None:
    """
    Read the final quality parameter of one Accept representation.

    Parameters
    ----------
    parameters : str
        Semicolon-delimited parameters following the media type.

    Returns
    -------
    float | None
        Quality value, or None if a quality parameter is malformed.
    """
    quality = 1.0
    for parameter in parameters.split(";"):
        name, separator, raw = parameter.strip().partition("=")
        if separator and name.lower() == "q":
            try:
                quality = float(raw)
            except ValueError:
                return None
    return quality

def _accepts_both(headers: Headers) -> bool:
    """
    Require explicitly acceptable JSON and event-stream representations.

    Parameters
    ----------
    headers : Headers
        Request headers containing the Accept representations.

    Returns
    -------
    bool
        Whether both representations are acceptable and qualities are valid.
    """
    accepted: set[str] = set()
    for value in headers.getAll("accept"):
        for entry in value.split(","):
            media, _, parameters = entry.partition(";")
            quality = _accept_quality(parameters) if parameters else 1.0
            if quality is None:
                return False
            if 0 < quality <= 1:
                accepted.add(media.strip().lower())
    return _ACCEPT_MEDIA_TYPES.issubset(accepted)

class McpHttpTransport:
    """Serve a registered endpoint without owning routes, sessions or identities."""

    __slots__ = ("_active", "_compiled", "_config", "_dispatcher", "_origins")

    def __init__(
        self,
        app: IApplication,
        compiled: CompiledMcpServer,
        config: McpConfig,
        bus: IMcpEventBus,
    ) -> None:
        """
        Retain immutable server metadata and one shared protocol dispatcher.

        Parameters
        ----------
        app : IApplication
            Application container supplying configuration and dependencies.
        compiled : CompiledMcpServer
            Precompiled metadata shared by request executions.
        config : McpConfig
            Validated configuration controlling this component.
        bus : IMcpEventBus
            Value supplied for ``bus``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._compiled = compiled
        self._config = config
        self._dispatcher = McpDispatcher(app, compiled, config, bus)
        self._origins = frozenset(config.allowed_origins)
        self._active = 0

    def _release(self) -> None:
        """
        Release a single request or response-stream admission slot.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._active -= 1

    def _validateHttp(self, request: Request) -> None:
        """
        Reject origins and unsupported media types before reading a body.

        Parameters
        ----------
        request : Request
            Current request and its trusted execution context.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        headers = request.headers
        if not origin_allowed(headers, self._origins):
            raise McpProtocolException(-32600, "Origin not allowed", status=403)
        if request.method != "POST":
            raise McpProtocolException(-32600, "Method not allowed", status=405)
        if not _accepts_both(headers):
            raise McpProtocolException(
                -32600,
                "Accept must include application/json and text/event-stream",
                status=406,
            )
        media = (headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if headers.count("content-type") != 1 or media != _JSON_MEDIA_TYPE:
            raise McpProtocolException(-32600, "Expected application/json", status=415)

    async def _read(self, request: Request) -> bytes:
        """
        Bound the native body stream before allocating the complete message.

        Parameters
        ----------
        request : Request
            Current request and its trusted execution context.

        Returns
        -------
        bytes
            Result of the operation described above.
        """
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > self._config.max_request_size:
                raise McpProtocolException(-32600, "Request body too large", status=413)
            content.extend(chunk)
        return bytes(content)

    def _params(self, request: Request, envelope: JsonRpcRequest) -> RequestParams:
        """
        Decode method parameters and validate compiled tool parameter headers.

        Parameters
        ----------
        request : Request
            Current request and its trusted execution context.
        envelope : JsonRpcRequest
            Value supplied for ``envelope``.

        Returns
        -------
        RequestParams
            Result of the operation described above.
        """
        params = self._dispatcher.decode(envelope)
        if isinstance(params, CallToolParams):
            tool = self._compiled.tools.get(
                params.name,
            ) or self._compiled.catalog_tools.get(params.name)
            if tool is not None:
                validate_headers(
                    request.headers, envelope, params, tool.mirrored_headers,
                )
        return params

    async def handle(self, request: Request) -> Response:
        """
        Validate HTTP metadata, dispatch once, and return native response objects.

        Parameters
        ----------
        request : Request
            Current request and its trusted execution context.

        Returns
        -------
        Response
            Result of the operation described above.
        """
        request_id = msgspec.UNSET
        admitted = False
        transferred = False
        try:
            self._validateHttp(request)
            if self._active >= self._config.max_concurrent_requests:
                raise McpProtocolException(
                    -32603, "Request capacity unavailable", status=503,
                )
            self._active += 1
            admitted = True
            envelope = decode_envelope(await self._read(request))
            request_id = envelope.id
            validate_headers(request.headers, envelope)
            if request_id is msgspec.UNSET:
                return Response(status_code=202)
            params = self._params(request, envelope)
            result = await self._dispatcher.dispatch(
                envelope,
                params,
                transport="http",
                native_request=request,
            )
            if isinstance(result.body, bytes):
                return McpProtocolResponse(
                    content=result.body,
                    status_code=result.status,
                    media_type=_JSON_MEDIA_TYPE,
                )
            events = _EventFrames(result.body, self._release)
            try:
                response = EventStreamResponse(events, status_code=result.status)
            except BaseException:
                transferred = True
                await events.aclose()
                raise
            transferred = True
            return response
        except McpProtocolException as exc:
            return self._error(exc, request_id)
        except PayloadTooLargeException:
            return self._error(
                McpProtocolException(-32600, "Request body too large", status=413),
                request_id,
            )
        except Exception:  # noqa: BLE001 - Transport failures must not expose internals.
            return self._error(
                McpProtocolException(-32603, "Internal error", status=500),
                request_id,
            )
        finally:
            if admitted and not transferred:
                self._release()

    def _error(
        self,
        exception: McpProtocolException,
        request_id: str | int | msgspec.UnsetType,
    ) -> Response:
        """
        Encode a sanitized protocol error with its required HTTP status.

        Parameters
        ----------
        exception : McpProtocolException
            Exception being inspected or reported.
        request_id : str | int | msgspec.UnsetType
            Value supplied for ``request_id``.

        Returns
        -------
        Response
            Result of the operation described above.
        """
        return McpProtocolResponse(
            content=encode_error(exception, request_id),
            status_code=exception.status,
            media_type=_JSON_MEDIA_TYPE,
            headers={"Allow": "POST"}
            if exception.status == HTTPStatus.METHOD_NOT_ALLOWED
            else None,
        )
