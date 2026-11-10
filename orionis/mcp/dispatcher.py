"""Provide mcp operations through ``DispatchResult``, ``McpDispatcher``."""

import asyncio
import base64
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, replace
import inspect
from typing import TYPE_CHECKING, Literal, cast
import msgspec
from orionis.failure.runtime import capture_result, operation
from orionis.http.adapters.response.streams import await_cleanup
from orionis.mcp.context import McpRequest
from orionis.mcp.exceptions import (
    McpAuthorizationException,
    McpInvalidParams,
    McpProtocolException,
)
from orionis.mcp.protocol.codecs import decode_envelope, decode_params, encode_error
from orionis.mcp.protocol.constants import (
    SERVER_INFO,
    SUBSCRIPTION_ID,
    SUPPORTED_VERSIONS,
)
from orionis.mcp.protocol.content import TextContent
from orionis.mcp.protocol.mrtr import validate_input_required, validate_input_responses
from orionis.mcp.protocol.requests import (
    CallToolParams,
    CompleteParams,
    GetPromptParams,
    InputResponseParams,
    JsonRpcRequest,
    ListenParams,
    PaginatedParams,
    PromptReference,
    ReadResourceParams,
    RequestParams,
    SubscriptionFilter,
)
from orionis.mcp.protocol.results import (
    CallToolResult,
    CompleteCompletionResult,
    CompleteResult,
    Completion,
    DiscoverResult,
    GetPromptResult,
    InputRequiredResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    Notification,
    ReadResourceResult,
    ResultResponse,
)
from orionis.mcp.protocol.validation import validate_result
from orionis.mcp.responses import McpResponse
from orionis.mcp.reporting import report
from orionis.mcp.normalization import (
    response_items,
    tool_result,
    prompt_result,
    resource_result,
    progress_params,
)
from orionis.mcp.server.compiler import (
    CompiledMcpServer,
    validate_output,
    validate_payload,
    validate_prompt_arguments,
)
from orionis.mcp.server.templates import validate_uri
from orionis.mcp.streams import OwnedStream
from orionis.schemas.exceptions.validation import ValidationException

if TYPE_CHECKING:
    from orionis.mcp.config import McpConfig
    from orionis.container.contracts.container import IContainer
    from orionis.http.request import Request
    from orionis.mcp.contracts.event_bus import IMcpEventBus
    from orionis.mcp.server.compiler import CompiledPrimitive, CompiledCatalog
    from orionis.mcp.normalization import CacheOptions

type TransportName = Literal["http", "stdio", "test"]
"""Type alias for ``Literal['http', 'stdio', 'test']``."""
_CURSOR_FIELDS = 2
"""Cursor fields value used by ``dispatcher``."""
_MAX_COMPLETIONS = 100
"""Max completions value used by ``dispatcher``."""
_DISCOVER_METHOD = "server/discover"
"""Discover method identifier: ``server/discover``."""
_TOOL_METHOD = "tools/call"
"""Tool method identifier: ``tools/call``."""
_PROMPT_METHOD = "prompts/get"
"""Prompt method identifier: ``prompts/get``."""
_INTERNAL_ERROR = "Internal error"
"""Error text for internal error: ``Internal error``."""
_INTERNAL_ERROR_CODE = -32603
"""JSON-RPC code identifying an unexpected application failure."""
_UNAVAILABLE_STATUS = 503
"""Expected admission rejection when bounded server capacity is unavailable."""
_RESULT_TYPES = {
    _TOOL_METHOD: CallToolResult,
    "resources/read": ReadResourceResult,
    _PROMPT_METHOD: GetPromptResult,
}
"""Result types definitions used by ``dispatcher``."""

@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Encoded JSON or a lazy stream of encoded notifications and final result."""

    body: bytes | AsyncIterator[bytes]
    """HTTP response body or encoded payload returned to the client."""
    status: int = 200
    """Status value used by ``DispatchResult``."""

    @property
    def streaming(self) -> bool:
        """
        Check whether the body requires streaming and request-scope retention.

        Returns
        -------
        bool
            ``True`` for an asynchronous body iterator; ``False`` for encoded bytes.
        """
        return not isinstance(self.body, bytes)

class McpDispatcher:
    """Perform no connection negotiation and retain no request or identity."""

    __slots__ = (
        "_extensions", "_list_sources", "_server_id", "app", "bus", "config", "server",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        app: IContainer,
        compiled: CompiledMcpServer,
        config: McpConfig,
        event_bus: IMcpEventBus,
    ) -> None:
        """
        Bind compiled server metadata and shared services for stateless dispatch.

        Parameters
        ----------
        app : orionis.container.contracts.container.IContainer
            Container used to build handlers and register request-scoped bindings.
        compiled : orionis.mcp.server.compiler.CompiledMcpServer
            Compiled server definitions, primitives, and extension metadata.
        config : orionis.mcp.config.McpConfig
            Limits and protocol options shared by dispatcher calls.
        event_bus : orionis.mcp.contracts.event_bus.IMcpEventBus
            Event service used to open change-notification subscriptions.

        Returns
        -------
        None
            Store shared services and precompute extension and listing lookups.
        """
        self.app = app
        """Application container supplying configuration and dependencies."""
        self.server = compiled
        """Precompiled metadata shared by request executions."""
        self.config = config
        """Validated configuration controlling this component."""
        self.bus = event_bus
        """Subscription service delivering server changes."""
        self._extensions = {
            method: (extension, handler)
            for extension in compiled.extensions
            for method, handler in extension.methods.items()
        }
        """Extensions registered for this server or transport."""
        self._server_id = (
            f"{compiled.definition.__module__}.{compiled.definition.__qualname__}"
        )
        """Stable server identifier used to bind protected request state."""
        self._list_sources = {
            "tools/list": (compiled.tools.values(), ListToolsResult, "tools"),
            "resources/list": (
                compiled.resources.values(), ListResourcesResult, "resources",
            ),
            "resources/templates/list": (
                compiled.templates, ListResourceTemplatesResult, "resourceTemplates",
            ),
            "prompts/list": (compiled.prompts.values(), ListPromptsResult, "prompts"),
        }
        """Compiled primitive collections used by listing operations."""

    def decode(self, envelope: JsonRpcRequest) -> RequestParams:
        """
        Validate core request metadata and decode method-specific parameters.

        Parameters
        ----------
        envelope : orionis.mcp.protocol.requests.JsonRpcRequest
            Decoded envelope whose method selects the parameter schema.

        Returns
        -------
        orionis.mcp.protocol.requests.RequestParams
            Validated core parameters or the extension decoder's typed parameters.

        Raises
        ------
        McpInvalidParams
            If an extension payload cannot be decoded.
        TypeError
            If an extension decoder returns something other than ``RequestParams``.
        """
        extension = self._extensions.get(envelope.method)
        if extension is None:
            return decode_params(envelope)
        core_params = decode_params(
            msgspec.structs.replace(envelope, method=_DISCOVER_METHOD),
        )
        decoder = extension[0].decoders.get(envelope.method)
        if decoder is None:
            return core_params
        try:
            params = decoder.decode(envelope.params)
        except msgspec.DecodeError as exc:
            raise McpInvalidParams from exc
        if not isinstance(params, RequestParams):
            message = "Extension parameters must inherit RequestParams"
            raise TypeError(message)
        return params

    async def handle(
        self,
        data: bytes,
        *,
        transport: TransportName = "test",
        native_request: Request | None = None,
    ) -> DispatchResult:
        """
        Decode and dispatch one envelope without adding transport framing.

        Parameters
        ----------
        data : bytes
            Encoded JSON-RPC envelope; the transport owns framing and request scope.
        transport : orionis.mcp.dispatcher.TransportName, optional
            Transport identifier recorded in execution and failure metadata.
        native_request : orionis.http.Request or None, optional
            Native request to attach to the execution context, when available.

        Returns
        -------
        orionis.mcp.dispatcher.DispatchResult
            Encoded reply or lazy byte stream. Notifications return an empty 202
            response; protocol decoding errors retain their response status.

        Raises
        ------
        BaseException
            If an unexpected decoder failure or unhandled control-flow
            interruption must propagate.
        """
        envelope = None
        try:
            if len(data) > self.config.max_request_size:
                raise McpProtocolException(-32600, "Request too large", status=413)
            envelope = decode_envelope(data)
            if envelope.id is msgspec.UNSET:
                return DispatchResult(b"", 202)
            params = self.decode(envelope)
        except McpProtocolException as exc:
            await self._report(
                exc, transport=transport, phase="decode", expected=True,
            )
            return DispatchResult(
                encode_error(exc, envelope.id if envelope else msgspec.UNSET),
                exc.status,
            )
        except BaseException as exc:
            await self._report(exc, transport=transport, phase="decode")
            raise
        return await self.dispatch(
            envelope, params, transport=transport, native_request=native_request,
        )

    async def dispatch(
        self,
        envelope: JsonRpcRequest,
        params: RequestParams,
        *,
        transport: TransportName = "test",
        native_request: Request | None = None,
    ) -> DispatchResult:
        """
        Execute a decoded request with shared policy checks and dependency bindings.

        Parameters
        ----------
        envelope : orionis.mcp.protocol.requests.JsonRpcRequest
            Envelope supplying the request identifier and method.
        params : orionis.mcp.protocol.requests.RequestParams
            Method parameters already decoded by ``decode`` or the transport.
        transport : orionis.mcp.dispatcher.TransportName, optional
            Transport identifier included in request context and failure metadata.
        native_request : orionis.http.Request or None, optional
            Native request to expose to handlers, when available.

        Returns
        -------
        orionis.mcp.dispatcher.DispatchResult
            Encoded result, sanitized error, or lazy byte stream. Notifications
            return an empty 202 response.

        Raises
        ------
        BaseException
            If cancellation or other non-``Exception`` control flow interrupts
            execution.
        """
        if envelope.id is msgspec.UNSET:
            return DispatchResult(b"", 202)
        with operation(
            self.app, flow="mcp", operation=envelope.method,
            correlation_id=str(envelope.id),
        ):
            try:
                if (
                    len(msgspec.json.encode(params.meta))
                    > self.config.max_metadata_size
                ):
                    msg = "Metadata too large"
                    raise McpInvalidParams(msg)
                request = self._request(envelope, params, transport, native_request)
                self.app.instance(McpRequest, request)
                self.app.instance(CompiledMcpServer, self.server)
                result = await self._execute(request, params)
                if isinstance(result, AsyncIterator):
                    return DispatchResult(result)
                return DispatchResult(self._encode(request, result))
            except McpProtocolException as exc:
                await self._report(
                    exc, transport=transport, phase="dispatch", expected=True,
                    correlation_id=envelope.id, operation_name=envelope.method,
                )
                return DispatchResult(encode_error(exc, envelope.id), exc.status)
            except Exception as exc:  # noqa: BLE001 - Public protocol boundary.
                await self._report(
                    exc, transport=transport, phase="dispatch",
                    correlation_id=envelope.id, operation_name=envelope.method,
                )
                error = McpProtocolException(-32603, _INTERNAL_ERROR, status=500)
                return DispatchResult(encode_error(error, envelope.id), error.status)
            except BaseException as exc:
                await self._report(
                    exc, transport=transport, phase="dispatch",
                    correlation_id=envelope.id, operation_name=envelope.method,
                )
                raise

    def _request(
        self,
        envelope: JsonRpcRequest,
        params: RequestParams,
        transport: TransportName,
        native: Request | None,
    ) -> McpRequest:
        """
        Build request context from the current envelope and typed parameters.

        Parameters
        ----------
        envelope : orionis.mcp.protocol.requests.JsonRpcRequest
            Envelope supplying the request identifier and method.
        params : orionis.mcp.protocol.requests.RequestParams
            Typed arguments, metadata, resource URI, and input-response retry state.
        transport : orionis.mcp.dispatcher.TransportName
            Transport identifier to store in the request context.
        native : orionis.http.Request or None
            Native request to expose in context, or ``None``.

        Returns
        -------
        orionis.mcp.McpRequest
            Context exposing arguments, metadata, retry state, and transport details.
        """
        retry = isinstance(params, InputResponseParams)
        responses = params.inputResponses if retry else msgspec.UNSET
        arguments = (
            params.arguments
            if isinstance(params, (CallToolParams, GetPromptParams))
            else {}
        )
        return McpRequest(
            id=cast("str | int", envelope.id),
            method=envelope.method,
            meta=params.meta,
            arguments=arguments,
            params=msgspec.to_builtins(params),
            uri=params.uri if isinstance(params, ReadResourceParams) else None,
            input_responses={} if responses is msgspec.UNSET else responses,
            request_state=params.requestState if retry else msgspec.UNSET,
            transport=transport,
            native_request=native,
            server_id=self._server_id,
        )

    async def _execute(self, request: McpRequest, params: RequestParams) -> object:
        """
        Route a decoded request to a core method, extension, or primitive.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Request context identifying the operation and its caller.
        params : orionis.mcp.protocol.requests.RequestParams
            Typed parameters selecting the operation and target primitive.

        Returns
        -------
        object
            Operation result, or an asynchronous byte stream for streamed calls.

        Raises
        ------
        McpProtocolException
            If the method is unsupported or an operation-specific protocol check fails.
        McpInvalidParams
            If the requested primitive is unknown or unavailable.
        """
        method = request.method
        if method in self._extensions:
            return await self._extension(request, params)
        if method == _DISCOVER_METHOD:
            return DiscoverResult(
                supportedVersions=SUPPORTED_VERSIONS,
                capabilities=self.server.capabilities_wire,
                instructions=self.server.instructions or msgspec.UNSET,
                **self._cache(),
            )
        if isinstance(params, PaginatedParams):
            return await self._list(request, params)
        if isinstance(params, ListenParams):
            return await self._listen(request, params)
        if isinstance(params, CompleteParams):
            return await self._complete(request, params)
        if isinstance(params, CallToolParams):
            primitive = self.server.tools.get(
                params.name,
            ) or self.server.catalog_tools.get(params.name)
        elif isinstance(params, GetPromptParams):
            primitive = self.server.prompts.get(params.name)
        elif isinstance(params, ReadResourceParams):
            primitive, request = self._resource(request, params.uri)
            self.app.instance(McpRequest, request, override=True)
        else:
            raise McpProtocolException(-32601, "Method not found", status=404)
        if primitive is None:
            msg = "Unknown or unavailable primitive"
            raise McpInvalidParams(
                msg, data={"uri": request.uri} if request.uri else msgspec.UNSET,
            )
        return await self._invoke(primitive, request)

    async def _extension(self, request: McpRequest, params: RequestParams) -> object:
        """
        Invoke an extension only when the client advertises its capability.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Request context containing the method and client capability metadata.
        params : orionis.mcp.protocol.requests.RequestParams
            Parameters accepted by the extension's decoder.

        Returns
        -------
        object
            Handler result, awaited when the extension returns an awaitable.

        Raises
        ------
        McpProtocolException
            If the client has not advertised the required extension capability.
        """
        extension, handler = self._extensions[request.method]
        supported = request.clientCapabilities.get("extensions", {})
        if not isinstance(supported, Mapping) or extension.identifier not in supported:
            raise McpProtocolException(
                -32021,
                "Missing required client capability",
                data={
                    "requiredCapabilities": {"extensions": {extension.identifier: {}}},
                },
            )
        result = handler(request, params)
        return await result if inspect.isawaitable(result) else result

    def _resource(
        self,
        request: McpRequest,
        uri: str,
    ) -> tuple[CompiledPrimitive | None, McpRequest]:
        """
        Resolve exact resource URIs before matching compiled URI templates.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Base request context to enrich when a URI template matches.
        uri : str
            Resource URI to validate and resolve.

        Returns
        -------
        tuple[CompiledPrimitive | None, McpRequest]
            Primitive and context, enriched with URI variables for a template
            match, or ``(None, request)`` when no definition matches.

        Raises
        ------
        McpInvalidParams
            If the supplied resource URI is invalid.
        """
        try:
            validate_uri(uri)
        except ValueError as exc:
            message = "Invalid resource URI"
            raise McpInvalidParams(message) from exc
        primitive = self.server.resources.get(uri)
        if primitive is not None:
            return primitive, request
        for candidate in self.server.templates:
            if candidate.matcher is None:
                continue
            variables = candidate.matcher.match(uri)
            if variables is not None:
                return candidate, replace(
                    request,
                    params={**request.params, **variables},
                    uri_variables=variables,
                )
        return None, request

    async def _access(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
        *,
        listing: bool = False,
    ) -> object | None:
        """
        Resolve a primitive handler and apply its request-specific access hooks.

        Return synthetic primitives directly without invoking handler access hooks.

        Parameters
        ----------
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Compiled tool, resource, prompt, or synthetic catalog declaration.
        request : orionis.mcp.McpRequest
            Context supplied to availability and authorization hooks.
        listing : bool, optional
            Return ``None`` for unavailable or unauthorized entries instead of raising.

        Returns
        -------
        object | None
            Resolved handler, the synthetic primitive itself, or ``None`` when a
            listing entry is denied.

        Raises
        ------
        McpInvalidParams
            If the primitive is unavailable and ``listing`` is false.
        McpAuthorizationException
            If authorization is denied and ``listing`` is false.
        """
        if primitive.synthetic:
            return primitive
        instance = await self.app.build(primitive.definition)
        if (
            primitive.availability is not None
            and not await primitive.availability.invoke(instance, self.app, request)
        ):
            if listing:
                return None
            msg = "Unknown or unavailable primitive"
            raise McpInvalidParams(
                msg, data={"uri": request.uri} if request.uri else msgspec.UNSET,
            )
        if (
            primitive.authorization is not None
            and not await primitive.authorization.invoke(instance, self.app, request)
        ):
            if listing:
                return None
            raise McpAuthorizationException
        return instance

    async def _invoke(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
    ) -> object:
        """
        Invoke a primitive through the shared policy and validation pipeline.

        Return tool-error results for invalid tool arguments and ordinary
        tool-handler failures.

        Parameters
        ----------
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Compiled tool, resource, prompt, or synthetic catalog declaration.
        request : orionis.mcp.McpRequest
            Context supplying arguments, retry state, and handler dependencies.

        Returns
        -------
        object
            Normalized result, input-required response, or owned stream of encoded
            messages.

        Raises
        ------
        McpProtocolException
            If access or protocol checks fail, or a non-tool handler raises.
        """
        self.app.instance(McpRequest, request, override=True)
        instance = await self._access(primitive, request)
        validate_input_responses(request.input_responses)
        try:
            payload = (
                await validate_payload(primitive, request.arguments)
                if request.method == _TOOL_METHOD
                else msgspec.UNSET
            )
        except (ValueError, TypeError, ValidationException) as exc:
            await self._report(exc, request, phase="validation", expected=True)
            return CallToolResult(
                content=(TextContent(text="Invalid tool arguments"),),
                isError=True,
            )
        if primitive.synthetic:
            return await self._catalog(primitive, request)
        if request.method == _PROMPT_METHOD:
            validate_prompt_arguments(primitive, request.arguments)
        try:
            if primitive.handler is None:
                message = "Missing compiled handler"
                raise RuntimeError(message)
            result = await primitive.handler.invoke(
                instance,
                self.app,
                request,
                payload,
            )
            if inspect.isasyncgen(result) or isinstance(result, AsyncIterator):
                source = OwnedStream(result)
                return OwnedStream(self._stream(primitive, request, source), source)
            if inspect.isgenerator(result):
                source = OwnedStream(result)
                return OwnedStream(self._stream(primitive, request, source), source)
            return await self._normalize(primitive, request, result)
        except McpProtocolException:
            raise
        except Exception as exc:
            await self._report(exc, request)
            if request.method == _TOOL_METHOD:
                return CallToolResult(
                    content=(TextContent(text="Tool execution failed"),),
                    isError=True,
                )
            raise McpProtocolException(-32603, _INTERNAL_ERROR, status=500) from exc

    async def _normalize(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
        result: object,
    ) -> object:
        """
        Normalize developer output into the requested method's validated result.

        Parameters
        ----------
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Primitive supplying output validation, descriptions, and cache policy.
        request : orionis.mcp.McpRequest
            Context identifying the result method and any input-response retry.
        result : object
            Developer return value or an already typed protocol result.

        Returns
        -------
        object
            Validated method result, including input-required or tool-error results
            when applicable.
        """
        if isinstance(result, InputRequiredResult):
            validate_input_required(result, request)
            validate_result(result, request.method)
            return result
        expected = _RESULT_TYPES[request.method]
        if isinstance(result, expected):
            if isinstance(result, CallToolResult) and result.isError is True:
                await capture_result(
                    "tool_error", app=self.app, flow="mcp", phase="result",
                    operation=request.method, correlation_id=str(request.id),
                    expected=True, metadata={"transport": request.transport},
                )
            if isinstance(result, CallToolResult) and result.isError is not True:
                await validate_output(primitive, result.structuredContent)
            if isinstance(result, ReadResourceResult):
                result = msgspec.structs.replace(
                    result, **self._cache(primitive, request),
                )
            validate_result(result, request.method)
            return result
        responses = response_items(result)
        if request.method == _TOOL_METHOD:
            normalized = await tool_result(primitive, responses)
        elif request.method == _PROMPT_METHOD:
            normalized = prompt_result(primitive.description, responses)
        else:
            normalized = resource_result(
                primitive, request, responses, self._cache(primitive, request),
            )
        validate_result(normalized, request.method)
        if isinstance(normalized, CallToolResult) and normalized.isError is True:
            await capture_result(
                "tool_error", app=self.app, flow="mcp", phase="result",
                operation=request.method, correlation_id=str(request.id),
                expected=True, metadata={"transport": request.transport},
            )
        return normalized

    async def _stream(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
        source: AsyncIterator[object],
    ) -> AsyncIterator[bytes]:
        """
        Yield progress notifications and a result with bounded response buffering.

        Enforce the response-size budget for accumulated non-progress values.

        Parameters
        ----------
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Primitive supplying result normalization and output validation.
        request : orionis.mcp.McpRequest
            Context supplying the response identifier and optional progress token.
        source : collections.abc.AsyncIterator[object]
            Primitive iterator to consume and close when streaming ends.

        Yields
        ------
        bytes
            Unframed JSON progress notifications when requested, followed by a
            result or sanitized error response.

        Raises
        ------
        BaseException
            If cancellation or other control flow escapes, or source cleanup fails.
        """
        responses = []
        used = 0
        previous = float("-inf")
        token = request.meta.get("progressToken", msgspec.UNSET)
        original = None
        try:
            async for item in source:
                if isinstance(item, McpResponse) and item.progress_update is not None:
                    update = item.progress_update
                    if token is msgspec.UNSET:
                        continue
                    params = progress_params(update, cast("str | int", token), previous)
                    previous = update.current
                    yield msgspec.json.encode(
                        Notification(method="notifications/progress", params=params),
                    )
                    continue
                used += len(msgspec.json.encode(item))
                if used > self.config.max_response_size:
                    error = "Response exceeds configured budget"
                    raise ValueError(error)
                responses.append(item)
            result = await self._normalize(
                primitive,
                request,
                responses[0] if len(responses) == 1 else responses,
            )
            yield self._encode(request, result)
        except McpProtocolException as exc:
            await self._report(exc, request, phase="stream", expected=True)
            yield encode_error(exc, request.id)
        except Exception as exc:  # noqa: BLE001 - Public protocol boundary.
            await self._report(exc, request, phase="stream")
            yield self._streamError(request)
        except BaseException as exc:
            original = exc
            await self._report(exc, request, phase="stream")
            raise
        finally:
            await self._finishStream(request, source, original)

    def _streamError(self, request: McpRequest) -> bytes:
        """
        Encode a sanitized result or protocol error for a failed primitive stream.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Context whose method selects a tool-error result or protocol error.

        Returns
        -------
        bytes
            Encoded tool-error result for tool calls, or an internal JSON-RPC error.
        """
        if request.method == _TOOL_METHOD:
            return self._encode(request, CallToolResult(
                content=(TextContent(text="Tool execution failed"),), isError=True,
            ))
        return encode_error(
            McpProtocolException(-32603, _INTERNAL_ERROR), request.id,
        )

    async def _finishStream(
        self, request: McpRequest, source: AsyncIterator[object],
        original: BaseException | None,
    ) -> None:
        """
        Close a primitive stream without replacing an escaping primary failure.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Request context attached to cleanup failure observation.
        source : collections.abc.AsyncIterator[object]
            Source whose optional asynchronous close hook should run.
        original : BaseException or None
            Escaping control-flow failure to preserve if cleanup also fails.

        Returns
        -------
        None
            Finish any asynchronous source cleanup.

        Raises
        ------
        BaseException
            If cleanup fails; re-raise ``original`` from that failure when supplied,
            otherwise propagate the cleanup failure.
        """
        try:
            await _close(source)
        except BaseException as exc:
            await self._report(exc, request, phase="cleanup")
            if original is not None:
                raise original from exc
            raise

    async def _list(self, request: McpRequest, params: PaginatedParams) -> object:
        """
        Build a bounded listing page after per-request access checks.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Context selecting a listing method and its access policies.
        params : orionis.mcp.protocol.requests.PaginatedParams
            Listing parameters containing the previous page boundary, if any.

        Returns
        -------
        object
            Method-specific listing with visible primitive metadata, a continuation
            cursor when needed, and server cache hints.

        Raises
        ------
        McpInvalidParams
            If the pagination cursor is invalid or belongs to another method.
        """
        values, result_type, field = self._list_sources[request.method]
        after = self._cursor(request.method, params.cursor)
        page = []
        last = ""
        next_cursor = msgspec.UNSET
        for primitive in values:
            if (
                primitive.name <= after
                or await self._access(primitive, request, listing=True) is None
            ):
                continue
            if len(page) >= self.config.default_page_size:
                next_cursor = base64.urlsafe_b64encode(
                    msgspec.json.encode([request.method, last]),
                ).decode("ascii")
                break
            page.append(primitive.metadata)
            last = primitive.name
        return result_type(
            **{field: tuple(page)},
            nextCursor=next_cursor,
            **self._cache(),
        )

    @staticmethod
    def _cursor(method: str, cursor: str | msgspec.UnsetType) -> str:
        """
        Decode and validate a stateless cursor for the requested listing method.

        Parameters
        ----------
        method : str
            Listing method to which the cursor must be bound.
        cursor : str | ``msgspec.UnsetType``
            Encoded cursor, or ``msgspec.UNSET`` for the first page.

        Returns
        -------
        str
            Last primitive name from the cursor, or ``""`` for the first page.

        Raises
        ------
        McpInvalidParams
            If the cursor encoding, contents, or bound method is invalid.
        """
        if cursor is msgspec.UNSET:
            return ""
        try:
            values = msgspec.json.decode(
                base64.b64decode(cursor, altchars=b"-_", validate=True),
            )
            if (
                isinstance(values, list)
                and len(values) == _CURSOR_FIELDS
                and values[0] == method
                and isinstance(values[1], str)
            ):
                return values[1]
        except (ValueError, msgspec.DecodeError) as exc:
            msg = "Invalid cursor"
            raise McpInvalidParams(msg) from exc
        msg = "Invalid cursor"
        raise McpInvalidParams(msg)

    def _cache(
        self,
        primitive: CompiledPrimitive | None = None,
        request: McpRequest | None = None,
    ) -> CacheOptions:
        """
        Select cache hints and disable caching for requests carrying retry state.

        Parameters
        ----------
        primitive : orionis.mcp.server.compiler.CompiledPrimitive or None, optional
            Primitive cache policy, or ``None`` to use server defaults.
        request : orionis.mcp.McpRequest or None, optional
            Request whose input-response or retry state can disable caching.

        Returns
        -------
        orionis.mcp.normalization.CacheOptions
            Cache fields ``ttlMs`` and ``cacheScope``. Input-response or request-state
            data forces zero TTL and private scope.
        """
        cache = primitive.cache if primitive is not None else self.server.cache
        if request is not None and (
            "inputResponses" in request.params
            or request.request_state is not msgspec.UNSET
        ):
            return {"ttlMs": 0, "cacheScope": "private"}
        return {"ttlMs": cache.ttl_ms, "cacheScope": cache.scope}

    def _encode(
        self, request: McpRequest, result: object,
        *, internal_meta: dict[str, object] | None = None,
    ) -> bytes:
        """
        Validate a result, attach server metadata, and encode its response.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Request supplying the response identifier and protocol method.
        result : object
            Completion or input-required result to validate and encode.
        internal_meta : dict[str, object] or None, optional
            Metadata merged over result metadata before server identity is set.

        Returns
        -------
        bytes
            JSON-RPC response bytes within the configured response-size budget.

        Raises
        ------
        TypeError
            If the result is neither a complete nor input-required result.
        ValueError
            If result metadata exceeds its configured size limit.
        McpProtocolException
            If the encoded response exceeds its configured size limit.
        """
        if not isinstance(result, (CompleteResult, InputRequiredResult)):
            message = "Invalid server result"
            raise TypeError(message)
        validate_result(result, request.method)
        if len(msgspec.json.encode(result.meta)) > self.config.max_metadata_size:
            message = "Result metadata exceeds configured limit"
            raise ValueError(message)
        metadata = {
            **result.meta, **(internal_meta or {}), SERVER_INFO: self.server.info,
        }
        result = msgspec.structs.replace(result, meta=metadata)
        encoded = msgspec.json.encode(ResultResponse(id=request.id, result=result))
        if len(encoded) > self.config.max_response_size:
            raise McpProtocolException(-32603, "Response too large", status=500)
        return encoded

    async def _complete(
        self,
        request: McpRequest,
        params: CompleteParams,
    ) -> CompleteCompletionResult:
        """
        Resolve completion values through the referenced primitive's access hooks.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Context supplied to access and completion hooks.
        params : orionis.mcp.protocol.requests.CompleteParams
            Reference, argument, and context for a prompt or template completion.

        Returns
        -------
        orionis.mcp.protocol.results.CompleteCompletionResult
            Completion containing a validated, bounded sequence of string values.

        Raises
        ------
        McpProtocolException
            If the server does not advertise completion support.
        McpInvalidParams
            If the reference, argument names, or returned completion values are invalid.
        """
        if "completions" not in self.server.capabilities:
            raise McpProtocolException(-32601, "Method not found", status=404)
        if isinstance(params.ref, PromptReference):
            primitive = self.server.prompts.get(params.ref.name)
        else:
            primitive = next(
                (item for item in self.server.templates if item.uri == params.ref.uri),
                None,
            )
        if primitive is None or primitive.completion is None:
            msg = "Unknown completion reference"
            raise McpInvalidParams(msg)
        if isinstance(params.ref, PromptReference):
            names = tuple(item.name for item in primitive.prompt_arguments)
        elif primitive.matcher:
            names = primitive.matcher.variable_names
        else:
            names = ()
        if params.argument.name not in names or (
            params.context is not msgspec.UNSET
            and any(name not in names for name in params.context.arguments)
        ):
            message = "Unknown completion argument"
            raise McpInvalidParams(message)
        instance = await self._access(primitive, request)
        value = await primitive.completion.invoke(instance, self.app, request)
        if isinstance(value, (tuple, list)):
            value = Completion(values=tuple(value))
        if not isinstance(value, Completion):
            raise McpInvalidParams
        if len(value.values) > _MAX_COMPLETIONS or any(
            not isinstance(item, str) for item in value.values
        ):
            msg = "Invalid completion result"
            raise McpInvalidParams(msg)
        return CompleteCompletionResult(completion=value)

    def _supports(self, capability: str, feature: str) -> bool:
        """
        Check whether a compiled capability explicitly enables a feature.

        Parameters
        ----------
        capability : str
            Compiled capability section to inspect.
        feature : str
            Feature flag within the capability mapping.

        Returns
        -------
        bool
            ``True`` only when the capability maps the feature to ``True``.
        """
        value = self.server.capabilities.get(capability)
        return isinstance(value, Mapping) and value.get(feature) is True

    async def _listen(
        self,
        request: McpRequest,
        params: ListenParams,
    ) -> AsyncIterator[bytes]:
        """
        Create a subscription stream from supported, currently authorized filters.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Request context used for resource-subscription access checks.
        params : orionis.mcp.protocol.requests.ListenParams
            Requested change notifications and resource-subscription URIs.

        Returns
        -------
        collections.abc.AsyncIterator[bytes]
            Owned byte stream carrying the accepted subscription filters and events.

        Raises
        ------
        McpInvalidParams
            If the resource-subscription count exceeds its limit or a checked URI
            is invalid.
        """
        filters = params.notifications
        if len(filters.resourceSubscriptions) > self.config.max_resource_subscriptions:
            msg = "Too many resource subscriptions"
            raise McpInvalidParams(msg)
        uris = []
        if self._supports("resources", "subscribe"):
            uris = [
                uri for uri in dict.fromkeys(filters.resourceSubscriptions)
                if await self._subscriptionResource(request, uri)
            ]
        accepted = SubscriptionFilter(
            toolsListChanged=filters.toolsListChanged
            and self._supports("tools", "listChanged"),
            promptsListChanged=filters.promptsListChanged
            and self._supports("prompts", "listChanged"),
            resourcesListChanged=filters.resourcesListChanged
            and self._supports("resources", "listChanged"),
            resourceSubscriptions=tuple(uris),
        )
        source = OwnedStream(self.bus.listen(self.server.definition, accepted))
        return OwnedStream(self._subscriptionStream(request, accepted, source), source)

    async def _subscriptionResource(self, request: McpRequest, uri: str) -> bool:
        """
        Check subscription access with a temporary resource-specific context.

        Restore the original request binding after access checks.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Original request context to restore after checking the resource.
        uri : str
            Resource URI whose existence and access hooks should be checked.

        Returns
        -------
        bool
            ``True`` for a known resource passing its access hooks; ``False`` for
            unknown, unavailable, or unauthorized resources.

        Raises
        ------
        McpInvalidParams
            If the resource URI is invalid.
        """
        primitive, resource_request = self._resource(replace(request, uri=uri), uri)
        if primitive is None:
            return False
        self.app.instance(McpRequest, resource_request, override=True)
        try:
            instance = await self._access(primitive, resource_request, listing=True)
            return instance is not None
        finally:
            self.app.instance(McpRequest, request, override=True)

    async def _subscriptionStream(
        self,
        request: McpRequest,
        filters: SubscriptionFilter,
        source: AsyncIterator[tuple[str, str | None]],
    ) -> AsyncIterator[bytes]:
        """
        Yield an acknowledgement, subscription events, and transport keepalives.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Context supplying subscription identity and transport behavior.
        filters : orionis.mcp.protocol.requests.SubscriptionFilter
            Accepted notification flags and resource subscriptions.
        source : collections.abc.AsyncIterator[tuple[str, str | None]]
            Change events containing a notification method and optional resource URI.

        Yields
        ------
        bytes
            Encoded acknowledgement, change notifications, and final completion.
            HTTP keepalives are ``b""``; stdio also emits a cancellation notification
            when the event source ends.

        Raises
        ------
        BaseException
            If event delivery or cleanup fails, or iteration is cancelled.
        """
        pending = None
        original = None
        metadata: dict[str, object] = {SUBSCRIPTION_ID: request.id}
        try:
            yield msgspec.json.encode(
                Notification(
                    method="notifications/subscriptions/acknowledged",
                    params={"_meta": metadata, "notifications": filters},
                ),
            )
            while True:
                if pending is None:
                    pending = asyncio.ensure_future(anext(source))
                done, _ = await asyncio.wait(
                    (pending,),
                    timeout=self.config.subscription_keepalive,
                )
                if not done:
                    if request.transport == "http":
                        yield b""
                    continue
                try:
                    method, uri = pending.result()
                except StopAsyncIteration:
                    break
                pending = None
                params: dict[str, object] = {"_meta": metadata}
                if uri is not None:
                    params["uri"] = uri
                yield msgspec.json.encode(Notification(method=method, params=params))
            if request.transport == "stdio":
                yield msgspec.json.encode(
                    Notification(
                        method="notifications/cancelled",
                        params={"requestId": request.id},
                    ),
                )
            yield self._encode(request, CompleteResult(), internal_meta=metadata)
        except BaseException as exc:
            original = exc
            await self._report(exc, request, phase="subscription")
            raise
        finally:
            await self._finishSubscription(request, pending, source, original)

    async def _finishSubscription(
        self, request: McpRequest, pending: asyncio.Future | None,
        source: object, original: BaseException | None,
    ) -> None:
        """
        Join pending subscription work and close the owned event source.

        Parameters
        ----------
        request : orionis.mcp.McpRequest
            Context attached to subscription cleanup failure observation.
        pending : asyncio.Future or None
            Pending source-advance operation to cancel and join, if any.
        source : object
            Event source whose optional asynchronous close hook should run.
        original : BaseException or None
            Escaping subscription failure to preserve if source cleanup also fails.

        Returns
        -------
        None
            Observe pending-operation failures and finish source cleanup.

        Raises
        ------
        BaseException
            If cleanup fails or caller cancellation must propagate. Keep
            ``original`` primary when source closure also fails.
        """
        try:
            if pending is not None:
                pending.cancel()
                results = await await_cleanup(
                    asyncio.gather(pending, return_exceptions=True),
                )
                for failure in results:
                    if isinstance(failure, BaseException) and not isinstance(
                        failure, StopAsyncIteration,
                    ):
                        await self._report(failure, request, phase="cleanup")
        finally:
            try:
                await _close(source)
            except BaseException as exc:
                await self._report(exc, request, phase="cleanup")
                if original is not None:
                    raise original from exc
                raise

    async def _catalog(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
    ) -> CallToolResult | InputRequiredResult:
        """
        Run a synthetic catalog search or batch-execution operation.

        Report tool-error outcomes and bound completed catalog responses by the
        configured output-size limit.

        Parameters
        ----------
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Synthetic primitive identifying the catalog and operation.
        request : orionis.mcp.McpRequest
            Context supplying search arguments or catalog tool calls.

        Returns
        -------
        CallToolResult or InputRequiredResult
            Tool-search or batch result, or a single-tool input-required response.

        Raises
        ------
        McpInvalidParams
            If the primitive has no catalog or completed output exceeds its budget.
        """
        if primitive.catalog is None:
            raise McpInvalidParams
        catalog = self.server.catalogs[primitive.catalog]
        response = (
            await self._searchCatalog(catalog, request)
            if primitive.synthetic == "search"
            else await self._executeCatalog(catalog, request)
        )
        if isinstance(response, InputRequiredResult):
            return response
        if (
            len(msgspec.json.encode(response))
            > self.config.tool_search_max_output_bytes
        ):
            message = "Catalog output limit exceeded"
            raise McpInvalidParams(message)
        if response.is_error:
            await capture_result(
                "tool_error", app=self.app, flow="mcp", phase="catalog",
                operation=request.method, correlation_id=str(request.id),
                expected=True, metadata={"transport": request.transport},
            )
        return CallToolResult(
            content=response.content, structuredContent=response.structured_content,
            isError=response.is_error,
        )

    async def _searchCatalog(
        self, catalog: CompiledCatalog, request: McpRequest,
    ) -> McpResponse:
        """
        Rank catalog text and return only request-accessible tool matches.

        Parameters
        ----------
        catalog : orionis.mcp.server.compiler.CompiledCatalog
            Compiled lexical index and tools available to this catalog.
        request : orionis.mcp.McpRequest
            Context supplying search terms, result limits, and access checks.

        Returns
        -------
        orionis.mcp.McpResponse
            Structured ``tools`` matches ordered by descending term score, then
            name, within the requested and configured result limits.
        """
        query = cast("str", request.arguments.get("query", ""))
        terms = query.casefold().split()
        limit = min(
            cast("int", request.arguments.get("limit", 10)),
            self.config.tool_search_max_results,
        )
        scored = sorted(
            (
                (sum(text.count(term) for term in terms), name)
                for name, text in catalog.index
            ),
            key=lambda item: (-item[0], item[1]),
        )
        matches = []
        for score, name in scored:
            if terms and not score:
                continue
            candidate = catalog.tools[name]
            if await self._access(candidate, request, listing=True) is not None:
                matches.append(msgspec.json.decode(candidate.metadata))
            if len(matches) >= limit:
                break
        return McpResponse.structured({"tools": matches})

    async def _executeCatalog(
        self, catalog: CompiledCatalog, request: McpRequest,
    ) -> McpResponse | InputRequiredResult:
        """
        Execute catalog tool calls sequentially with shared validation and access.

        Stop after the first tool error. Return an error when a multi-call batch
        requires additional input, preserving input-required results for single calls.

        Parameters
        ----------
        catalog : orionis.mcp.server.compiler.CompiledCatalog
            Compiled tools that this catalog permits callers to execute.
        request : orionis.mcp.McpRequest
            Context containing the ordered tool-call batch.

        Returns
        -------
        McpResponse or InputRequiredResult
            Completed call results, a batch input-required error, or a single-call
            input-required protocol response.

        Raises
        ------
        McpInvalidParams
            If the call count, target name, or accumulated output size is invalid.
        """
        calls = cast("tuple[Mapping[str, object], ...]", request.arguments["calls"])
        if not 0 < len(calls) <= self.config.tool_search_max_calls:
            message = "Invalid catalog call count"
            raise McpInvalidParams(message)
        outputs = []
        size = 0
        for call in calls:
            target = catalog.tools.get(cast("str", call["name"]))
            if target is None:
                message = "Unknown catalog tool"
                raise McpInvalidParams(message)
            nested = replace(
                request,
                arguments=cast("Mapping[str, object]", call.get("arguments", {})),
                params={
                    **request.params, "name": call["name"],
                    "arguments": call.get("arguments", {}),
                },
            )
            try:
                result = await self._invoke(target, nested)
                result_value = await self._catalogResult(result)
            finally:
                self.app.instance(McpRequest, request, override=True)
            if result_value.get("resultType") == "input_required":
                if len(calls) == 1:
                    metadata = cast("dict[str, object]", result_value.get("_meta", {}))
                    metadata.pop(SERVER_INFO, None)
                    return msgspec.convert(result_value, type=InputRequiredResult)
                return McpResponse.error(
                    "A catalog tool requires additional input. Call that tool "
                    "individually; completed batch calls must not be replayed.",
                )
            size += len(msgspec.json.encode(result_value))
            if size > self.config.tool_search_max_output_bytes:
                message = "Catalog output limit exceeded"
                raise McpInvalidParams(message)
            outputs.append({"name": call["name"], "result": result_value})
            if result_value.get("isError"):
                break
        return McpResponse.structured({"results": outputs})

    @staticmethod
    async def _catalogResult(result: object) -> dict[str, object]:
        """
        Extract a catalog result while discarding intermediate stream notifications.

        Parameters
        ----------
        result : object
            Immediate tool result or asynchronous stream of encoded protocol messages.

        Returns
        -------
        dict[str, object]
            Built-in immediate result, or the last result mapping received from
            the stream.

        Raises
        ------
        McpInvalidParams
            If a stream emits a protocol error or finishes without a result.
        """
        if not isinstance(result, AsyncIterator):
            return msgspec.to_builtins(result)
        final = None
        try:
            async for message in result:
                if not message:
                    continue
                decoded = msgspec.json.decode(message)
                if "result" in decoded:
                    final = decoded["result"]
                elif "error" in decoded:
                    error = "Catalog tool failed"
                    raise McpInvalidParams(error)
        finally:
            await _close(result)
        if final is None:
            error = "Catalog tool did not return a result"
            raise McpInvalidParams(error)
        return final

    async def _report(  # noqa: PLR0913 - Explicit error-only context fields.
        self, exception: BaseException, request: McpRequest | None = None,
        *, transport: str = "in-process", phase: str = "execution",
        expected: bool = False, correlation_id: str | int | None = None,
        operation_name: str | None = None,
    ) -> None:
        """
        Observe a dispatch failure with normalized request and error context.

        Reclassify JSON-RPC internal errors by status, treating 503 as expected.
        If such an error wraps an ``Exception``, report its cause as unexpected.

        Parameters
        ----------
        exception : BaseException
            Failure to observe, optionally unwrapped from an internal protocol error.
        request : orionis.mcp.McpRequest or None, optional
            Context whose transport, method, and identifier override fallbacks.
        transport : str, optional
            Transport name used when no request context is supplied.
        phase : str, optional
            Execution or lifecycle phase attached to the failure.
        expected : bool, optional
            Expected-failure flag, overridden for internal errors as described above.
        correlation_id : str | int | None, optional
            Request identifier used when ``request`` is absent.
        operation_name : str or None, optional
            Protocol method or operation name used without request context.

        Returns
        -------
        None
            Await shared MCP failure observation without constructing a reply.
        """
        if (
            isinstance(exception, McpProtocolException)
            and exception.code == _INTERNAL_ERROR_CODE
        ):
            expected = exception.status == _UNAVAILABLE_STATUS
            if isinstance(exception.__cause__, Exception):
                exception = exception.__cause__
                expected = False
        await report(
            exception, self.app,
            transport=request.transport if request is not None else transport,
            phase=phase, expected=expected,
            operation=request.method if request is not None else operation_name,
            correlation_id=request.id if request is not None else correlation_id,
        )

async def _close(source: object) -> None:
    """
    Await a source's asynchronous close hook when one is available.

    Parameters
    ----------
    source : object
        Object optionally exposing an awaitable ``aclose`` method.

    Returns
    -------
    None
        Finish the close hook, or do nothing when ``aclose`` is absent.

    Raises
    ------
    BaseException
        If the asynchronous close hook fails or is cancelled.
    """
    close = getattr(source, "aclose", None)
    if close is not None:
        await close()
