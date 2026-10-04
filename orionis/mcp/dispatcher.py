"""The common stateless dispatcher used by HTTP, STDIO and in-process tests."""

import asyncio
import base64
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, replace
import inspect
from typing import TYPE_CHECKING, Literal, cast

import msgspec

from orionis.mcp.context import McpRequest, mutable_json
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
_CURSOR_FIELDS = 2
_MAX_COMPLETIONS = 100


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Encoded JSON or a lazy stream of encoded notifications and final result."""

    body: bytes | AsyncIterator[bytes]
    status: int = 200

    @property
    def streaming(self) -> bool:
        """Indicate whether the transport must preserve the request scope."""
        return not isinstance(self.body, bytes)


class McpDispatcher:
    """Perform no connection negotiation and retain no request or identity."""

    __slots__ = ("_extensions", "app", "bus", "config", "server")

    def __init__(
        self,
        app: IContainer,
        compiled: CompiledMcpServer,
        config: McpConfig,
        event_bus: IMcpEventBus,
    ) -> None:
        """Share immutable definitions and bounded worker services."""
        self.app = app
        self.server = compiled
        self.config = config
        self.bus = event_bus
        self._extensions = {
            method: (extension, handler)
            for extension in compiled.extensions
            for method, handler in extension.methods.items()
        }

    def decode(self, envelope: JsonRpcRequest) -> RequestParams:
        """Validate core metadata before an extension's precompiled decoder."""
        extension = self._extensions.get(envelope.method)
        if extension is None:
            return decode_params(envelope)
        decode_params(msgspec.structs.replace(envelope, method="server/discover"))
        decoder = extension[0].decoders.get(envelope.method)
        if decoder is None:
            return decode_params(
                msgspec.structs.replace(envelope, method="server/discover"),
            )
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
        """Decode one message; transports supply their own framing and scope."""
        envelope = None
        try:
            if len(data) > self.config.max_request_size:
                raise McpProtocolException(-32600, "Request too large", status=413)
            envelope = decode_envelope(data)
            if envelope.id is msgspec.UNSET:
                return DispatchResult(b"", 202)
            params = self.decode(envelope)
            return await self.dispatch(
                envelope,
                params,
                transport=transport,
                native_request=native_request,
            )
        except McpProtocolException as exc:
            return DispatchResult(
                encode_error(exc, envelope.id if envelope else msgspec.UNSET),
                exc.status,
            )

    async def dispatch(
        self,
        envelope: JsonRpcRequest,
        params: RequestParams,
        *,
        transport: TransportName = "test",
        native_request: Request | None = None,
    ) -> DispatchResult:
        """Execute the same availability, authorization and DI on every transport."""
        if envelope.id is msgspec.UNSET:
            return DispatchResult(b"", 202)
        try:
            if len(msgspec.json.encode(params.meta)) > self.config.max_metadata_size:
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
            return DispatchResult(encode_error(exc, envelope.id), exc.status)
        except Exception as exc:  # noqa: BLE001 - Public protocol boundary.
            await self._report(exc)
            error = McpProtocolException(-32603, "Internal error", status=500)
            return DispatchResult(encode_error(error, envelope.id), error.status)

    def _request(
        self,
        envelope: JsonRpcRequest,
        params: RequestParams,
        transport: TransportName,
        native: Request | None,
    ) -> McpRequest:
        """Create context from typed parameters, never from connection history."""
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
            server_id=(
                f"{self.server.definition.__module__}."
                f"{self.server.definition.__qualname__}"
            ),
        )

    async def _execute(self, request: McpRequest, params: RequestParams) -> object:
        """Route known core methods without reflection or dynamic imports."""
        method = request.method
        if method in self._extensions:
            return await self._extension(request, params)
        if method == "server/discover":
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
        """Run an explicitly negotiated extension without implicit capabilities."""
        extension, handler = self._extensions[request.method]
        supported = request.client_capabilities.get("extensions", {})
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
        """Prefer exact URI lookup before compiled RFC 6570 template matchers."""
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
        """Resolve fresh handlers and enforce both independent access hooks."""
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
        """Share one execution path between direct and catalog calls."""
        self.app.instance(McpRequest, request, override=True)
        instance = await self._access(primitive, request)
        validate_input_responses(request.input_responses)
        try:
            payload = (
                validate_payload(primitive, mutable_json(request.arguments))
                if request.method == "tools/call"
                else msgspec.UNSET
            )
        except ValueError, TypeError, ValidationException:
            return CallToolResult(
                content=(TextContent(text="Invalid tool arguments"),),
                isError=True,
            )
        if primitive.synthetic:
            return await self._catalog(primitive, request)
        if request.method == "prompts/get":
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
            return self._normalize(primitive, request, result)
        except McpProtocolException:
            raise
        except Exception as exc:
            await self._report(exc)
            if request.method == "tools/call":
                return CallToolResult(
                    content=(TextContent(text="Tool execution failed"),),
                    isError=True,
                )
            raise McpProtocolException(-32603, "Internal error", status=500) from exc

    def _normalize(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
        result: object,
    ) -> object:
        """Convert developer responses into the method's exact result type."""
        if isinstance(result, InputRequiredResult):
            validate_input_required(result, request)
            validate_result(result, request.method)
            return result
        expected = {
            "tools/call": CallToolResult,
            "resources/read": ReadResourceResult,
            "prompts/get": GetPromptResult,
        }[request.method]
        if isinstance(result, expected):
            if isinstance(result, CallToolResult) and result.isError is not True:
                validate_output(primitive, result.structuredContent)
            if isinstance(result, ReadResourceResult):
                result = msgspec.structs.replace(
                    result, **self._cache(primitive, request),
                )
            validate_result(result, request.method)
            return result
        responses = response_items(result)
        if request.method == "tools/call":
            normalized = tool_result(primitive, responses)
        elif request.method == "prompts/get":
            normalized = prompt_result(primitive.description, responses)
        else:
            normalized = resource_result(
                primitive, request, responses, self._cache(primitive, request),
            )
        validate_result(normalized, request.method)
        return normalized

    async def _stream(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
        source: AsyncIterator[object],
    ) -> AsyncIterator[bytes]:
        """Pull notifications with transport backpressure and close on cancellation."""
        responses = []
        used = 0
        previous = float("-inf")
        token = request.meta.get("progressToken", msgspec.UNSET)
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
            result = self._normalize(
                primitive,
                request,
                responses[0] if len(responses) == 1 else responses,
            )
            yield self._encode(request, result)
        except McpProtocolException as exc:
            yield encode_error(exc, request.id)
        except Exception as exc:  # noqa: BLE001 - Public protocol boundary.
            await self._report(exc)
            if request.method == "tools/call":
                yield self._encode(request, CallToolResult(
                    content=(TextContent(text="Tool execution failed"),), isError=True,
                ))
            else:
                yield encode_error(
                    McpProtocolException(-32603, "Internal error"), request.id,
                )
        finally:
            close = getattr(source, "aclose", None)
            if close is not None:
                await close()

    async def _list(self, request: McpRequest, params: PaginatedParams) -> object:
        """Build a bounded deterministic page after request-specific access checks."""
        sources = {
            "tools/list": (self.server.tools.values(), ListToolsResult, "tools"),
            "resources/list": (
                self.server.resources.values(),
                ListResourcesResult,
                "resources",
            ),
            "resources/templates/list": (
                self.server.templates,
                ListResourceTemplatesResult,
                "resourceTemplates",
            ),
            "prompts/list": (
                self.server.prompts.values(),
                ListPromptsResult,
                "prompts",
            ),
        }
        values, result_type, field = sources[request.method]
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
        """Decode a cursor without retaining any server-side pagination state."""
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
        """Never share retry results or default request-dependent content publicly."""
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
        """Attach precompiled identity and encode the response exactly once."""
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
        """Run completion through the referenced primitive's access policy."""
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
        names = (
            tuple(item.name for item in primitive.prompt_arguments)
            if isinstance(params.ref, PromptReference)
            else primitive.matcher.variable_names if primitive.matcher else ()
        )
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
        """Read one static compiled capability hint."""
        value = self.server.capabilities.get(capability)
        return isinstance(value, Mapping) and value.get(feature) is True

    async def _listen(
        self,
        request: McpRequest,
        params: ListenParams,
    ) -> AsyncIterator[bytes]:
        """Accept only supported changes and resource URIs authorized right now."""
        filters = params.notifications
        if len(filters.resourceSubscriptions) > self.config.max_resource_subscriptions:
            msg = "Too many resource subscriptions"
            raise McpInvalidParams(msg)
        uris = []
        if self._supports("resources", "subscribe"):
            uris = [
                uri for uri in dict.fromkeys(filters.resourceSubscriptions)
                if await self._subscription_resource(request, uri)
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
        return OwnedStream(self._subscription_stream(request, accepted, source), source)

    async def _subscription_resource(self, request: McpRequest, uri: str) -> bool:
        """Give all admission dependencies the same resource-specific context."""
        primitive, resource_request = self._resource(replace(request, uri=uri), uri)
        if primitive is None:
            return False
        self.app.instance(McpRequest, resource_request, override=True)
        try:
            instance = await self._access(primitive, resource_request, listing=True)
            return instance is not None
        finally:
            self.app.instance(McpRequest, request, override=True)

    async def _subscription_stream(
        self,
        request: McpRequest,
        filters: SubscriptionFilter,
        source: AsyncIterator[tuple[str, str | None]],
    ) -> AsyncIterator[bytes]:
        """Acknowledge before events; use SSE comments for idle keepalive."""
        pending = None
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
        finally:
            if pending is not None:
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            await _close(source)

    async def _catalog(
        self,
        primitive: CompiledPrimitive,
        request: McpRequest,
    ) -> CallToolResult | InputRequiredResult:
        """Bound lexical search and reuse the ordinary execution pipeline."""
        if primitive.catalog is None:
            raise McpInvalidParams
        catalog = self.server.catalogs[primitive.catalog]
        response = (
            await self._search_catalog(catalog, request)
            if primitive.synthetic == "search"
            else await self._execute_catalog(catalog, request)
        )
        if isinstance(response, InputRequiredResult):
            return response
        if (
            len(msgspec.json.encode(response))
            > self.config.tool_search_max_output_bytes
        ):
            message = "Catalog output limit exceeded"
            raise McpInvalidParams(message)
        return CallToolResult(
            content=response.content, structuredContent=response.structured_content,
            isError=response.is_error,
        )

    async def _search_catalog(
        self, catalog: CompiledCatalog, request: McpRequest,
    ) -> McpResponse:
        """Rank precompiled text deterministically after request-specific checks."""
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

    async def _execute_catalog(
        self, catalog: CompiledCatalog, request: McpRequest,
    ) -> McpResponse | InputRequiredResult:
        """Execute a bounded batch through the same policy and validation path."""
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
                result_value = await self._catalog_result(result)
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
    async def _catalog_result(result: object) -> dict[str, object]:
        """Discard intermediate notifications without accumulating their bytes."""
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

    async def _report(self, exception: Exception) -> None:
        """Use the native reporting hook without invoking HTML/CLI presentation."""
        try:
            get_handler = getattr(self.app, "getExceptionHandler", None)
            if get_handler is None:
                return
            handler = await get_handler()
            await self.app.call(handler, "report", exception=exception)
        except Exception:  # noqa: BLE001 - Do not mask the original failure.
            # Reporting must not turn an internal error into a second public failure.
            return


async def _close(source: object) -> None:
    """Close an optionally closable async source without retaining it."""
    close = getattr(source, "aclose", None)
    if close is not None:
        await close()
