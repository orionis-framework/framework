"""Compile immutable registries, native schemas and binders at application boot."""

import re
from dataclasses import dataclass, field, replace
from types import MappingProxyType, get_original_bases
from typing import Annotated, Literal, get_args, get_origin, TYPE_CHECKING, cast

import msgspec

from orionis.mcp.context import freeze_json, mutable_json
from orionis.mcp.exceptions import McpInvalidParams
from orionis.mcp.invoker import McpInvoker
from orionis.mcp.protocol.metadata import (
    CacheHint,
    PromptArgument,
    PromptMetadata,
    ResourceMetadata,
    ServerInfo,
    ToolMetadata,
)
from orionis.mcp.protocol.metavalidation import validate_metadata
from orionis.mcp.server.catalog import ToolCatalog
from orionis.mcp.server.extension import McpExtension
from orionis.mcp.server.primitives import Primitive, Prompt, Resource, Server, Tool
from orionis.mcp.server.schemas import compile_schema, convert_payload
from orionis.mcp.server.templates import UriMatcher, validate_uri
from orionis.mcp.transport.headers import HeaderBinding, compile_header_bindings

if TYPE_CHECKING:
    from collections.abc import Mapping

_NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}")
_CORE_METHODS = frozenset(
    {
        "server/discover",
        "ping",
        "tools/list",
        "tools/call",
        "resources/list",
        "resources/templates/list",
        "resources/read",
        "prompts/list",
        "prompts/get",
        "completion/complete",
        "subscriptions/listen",
        "initialize",
    },
)


class _SearchPayload(msgspec.Struct, forbid_unknown_fields=True):
    """Bounded searchable catalog arguments."""

    query: Annotated[str, msgspec.Meta(max_length=4096)] = ""
    limit: Annotated[int, msgspec.Meta(ge=1, le=100)] = 10


class _CatalogCall(msgspec.Struct, forbid_unknown_fields=True):
    """An independent catalog invocation, with no Python call kwargs."""

    name: str
    arguments: dict[str, object] = msgspec.field(default_factory=dict)


class _ExecutePayload(msgspec.Struct, forbid_unknown_fields=True):
    """Request limits are additionally enforced by the dispatcher configuration."""

    calls: Annotated[list[_CatalogCall], msgspec.Meta(min_length=1)]


@dataclass(frozen=True, slots=True, kw_only=True)
class CompiledPrimitive:
    """Unbound declaration metadata, with no identity or per-call service instance."""

    definition: type[Primitive]
    name: str
    metadata: msgspec.Raw
    handler: McpInvoker | None
    description: str = ""
    availability: McpInvoker | None = None
    authorization: McpInvoker | None = None
    completion: McpInvoker | None = None
    input_type: object = None
    output_type: object = msgspec.UNSET
    input_schema: msgspec.Raw | None = None
    output_schema: msgspec.Raw | None = None
    mirrored_headers: tuple[HeaderBinding, ...] = ()
    cache: CacheHint = field(default_factory=CacheHint)
    uri: str | None = None
    mime_type: str | None = None
    prompt_arguments: tuple[PromptArgument, ...] = ()
    matcher: UriMatcher | None = None
    synthetic: Literal["search", "execute"] | None = None
    catalog: int | None = None
    search_text: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompiledCatalog:
    """One hidden catalog and its deterministic boot-time lexical index."""

    tools: Mapping[str, CompiledPrimitive]
    search_name: str
    execute_name: str
    index: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CompiledMcpServer:
    """A definition reusable by every request, worker and supported transport."""

    definition: type[Server]
    tools: Mapping[str, CompiledPrimitive]
    resources: Mapping[str, CompiledPrimitive]
    prompts: Mapping[str, CompiledPrimitive]
    templates: tuple[CompiledPrimitive, ...]
    info: ServerInfo
    capabilities: Mapping[str, object]
    capabilities_wire: msgspec.Raw
    instructions: str
    cache: CacheHint
    extensions: tuple[McpExtension, ...]
    catalog_tools: Mapping[str, CompiledPrimitive]
    catalogs: tuple[CompiledCatalog, ...]


def _wire(value: object) -> msgspec.Raw:
    """Freeze wire metadata into immutable JSON without retaining mutable maps."""
    return msgspec.Raw(msgspec.json.encode(value))


def _validate_static_metadata(metadata: dict[str, object], kind: type) -> None:
    """Check declaration constructors once, keeping validation off list hot paths."""
    expected = {Tool: ToolMetadata, Resource: ResourceMetadata, Prompt: PromptMetadata}
    msgspec.convert(msgspec.to_builtins(metadata), type=expected[kind], strict=True)
    if "_meta" in metadata:
        validate_metadata(metadata["_meta"], allow_reserved=False)


def _extend_metadata(
    metadata: dict[str, object], extensions: tuple[McpExtension, ...],
) -> dict[str, object]:
    """Let extensions attach data without changing compiled native contracts."""
    if not extensions:
        return metadata
    baseline = cast("dict[str, object]", mutable_json(metadata))
    extended = cast("dict[str, object]", mutable_json(baseline))
    for extension in extensions:
        if extension.schema_hook is not None:
            extension.schema_hook(extended)
    for key in (
        "name", "title", "description", "icons", "annotations", "inputSchema",
        "outputSchema", "uri", "uriTemplate", "mimeType", "size", "arguments",
    ):
        if extended.get(key, msgspec.UNSET) != baseline.get(key, msgspec.UNSET):
            message = (
                "Extension schema hooks may attach extension metadata but cannot "
                f"change compiled standard field {key!r}."
            )
            raise ValueError(message)
    return extended


def _name(definition: type[Primitive]) -> str:
    """Derive readable kebab names while honoring explicit protocol identifiers."""
    if definition.name:
        name = definition.name
    else:
        stem = definition.__name__
        for suffix in ("Tool", "Resource", "Prompt"):
            if stem.endswith(suffix):
                stem = stem.removesuffix(suffix)
                break
        stem = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", stem)
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", stem).replace("_", "-").lower()
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        message = f"Invalid MCP primitive name {name!r}."
        raise ValueError(message)
    return name


def _metadata(definition: type[Primitive], name: str) -> dict[str, object]:
    """Snapshot common metadata before adding primitive-specific wire fields."""
    metadata: dict[str, object] = {"name": name}
    for key in ("title", "description", "icons"):
        value = getattr(definition, key)
        if value:
            metadata[key] = value
    if definition.meta:
        metadata["_meta"] = mutable_json(definition.meta)
    return metadata


def _hook(definition: type, method: str) -> McpInvoker | None:
    """Compile optional per-request checks without resolving a handler instance."""
    return (
        McpInvoker.compile(definition, method) if hasattr(definition, method) else None
    )


def _tool_types(definition: type[Tool]) -> tuple[object, object]:
    """Accept explicit declarations or the one/two-parameter Python generic API."""
    input_type = definition.input
    output_type = definition.output
    for ancestor in definition.__mro__:
        for base in get_original_bases(ancestor):
            if get_origin(base) is Tool:
                args = get_args(base)
                if input_type is None and args and args[0] is not object:
                    input_type = args[0]
                if output_type is None and len(args) > 1 and args[1] is not object:
                    output_type = args[1]
    return input_type, msgspec.UNSET if output_type is None else output_type


class _Compiler:
    """Own only boot-time schema caches; discard them after the registry is built."""

    __slots__ = ("cache", "extensions", "schemas")

    def __init__(self, extensions: tuple[McpExtension, ...], cache: CacheHint) -> None:
        """Use a per-compilation cache rather than growing a process-global cache."""
        self.schemas: dict[tuple[object, bool], dict[str, object]] = {}
        self.extensions = extensions
        self.cache = cache

    def schema(self, annotation: object, *, input_schema: bool) -> dict[str, object]:
        """Share one schema snapshot per type and direction inside this compilation."""
        key = (annotation, input_schema)
        if key not in self.schemas:
            self.schemas[key] = compile_schema(annotation, input_schema=input_schema)
        return self.schemas[key]

    def primitive(
        self, definition: type[Primitive], kind: type[Primitive],
    ) -> CompiledPrimitive:
        """Compile one ordinary primitive and all of its immutable handler plans."""
        if not isinstance(definition, type) or not issubclass(definition, kind):
            message = f"Server definitions must contain {kind.__name__} classes."
            raise TypeError(message)
        name = _name(definition)
        metadata = _metadata(definition, name)
        cache = self.cache
        for ancestor in definition.__mro__:
            if ancestor is Primitive:
                break
            if "cache" in vars(ancestor):
                cache = ancestor.cache
                break
        primitive = CompiledPrimitive(
            definition=definition,
            name=name,
            description=definition.description,
            metadata=msgspec.Raw(b"{}"),
            handler=None,
            cache=cache,
            availability=_hook(definition, "shouldRegister"),
            authorization=_hook(definition, "authorize"),
            completion=_hook(definition, "complete"),
        )
        if kind is Tool:
            primitive = self._tool(cast("type[Tool]", definition), primitive, metadata)
        elif kind is Resource:
            primitive = self._resource(
                cast("type[Resource]", definition), primitive, metadata,
            )
        else:
            primitive = self._prompt(
                cast("type[Prompt]", definition), primitive, metadata,
            )
        metadata = _extend_metadata(metadata, self.extensions)
        _validate_static_metadata(metadata, kind)
        return replace(
            primitive,
            metadata=_wire(metadata),
            search_text=msgspec.json.encode(metadata).decode("utf-8").lower(),
        )

    def _tool(
        self,
        definition: type[Tool],
        primitive: CompiledPrimitive,
        metadata: dict[str, object],
    ) -> CompiledPrimitive:
        """Compile typed tool schemas and statically reachable header bindings."""
        input_type, output_type = _tool_types(definition)
        schema = (
            self.schema(input_type, input_schema=True)
            if input_type is not None
            else {
                "type": "object",
                "additionalProperties": False,
            }
        )
        output_schema = None
        metadata["inputSchema"] = schema
        if output_type is not msgspec.UNSET:
            output_schema = self.schema(output_type, input_schema=False)
            metadata["outputSchema"] = output_schema
        if definition.annotations is not None:
            metadata["annotations"] = definition.annotations
        return replace(
            primitive,
            input_type=input_type,
            output_type=output_type,
            input_schema=_wire(schema),
            output_schema=_wire(output_schema) if output_schema is not None else None,
            mirrored_headers=compile_header_bindings(schema),
            handler=McpInvoker.compile(definition, "handle", input_type),
        )

    @staticmethod
    def _resource(
        definition: type[Resource],
        primitive: CompiledPrimitive,
        metadata: dict[str, object],
    ) -> CompiledPrimitive:
        """Compile exact resources and RFC templates with safe inverse matching."""
        if bool(definition.uri) == bool(definition.uri_template):
            message = "A Resource must declare exactly one URI or URI template."
            raise ValueError(message)
        matcher = None
        uri_names: tuple[str, ...] = ()
        if definition.uri_template:
            matcher = UriMatcher.compile(definition)
            uri_names = matcher.variable_names
            metadata["uriTemplate"] = definition.uri_template
        else:
            validate_uri(definition.uri)
            metadata["uri"] = definition.uri
        metadata["mimeType"] = definition.mime_type
        if definition.annotations is not None:
            metadata["annotations"] = definition.annotations
        if definition.size is not None:
            if type(definition.size) is not int or definition.size < 0:
                message = "Resource size must be a nonnegative integer."
                raise ValueError(message)
            metadata["size"] = definition.size
        return replace(
            primitive,
            matcher=matcher,
            uri=definition.uri or definition.uri_template,
            mime_type=definition.mime_type,
            handler=McpInvoker.compile(definition, "handle", uri_names=uri_names),
        )

    @staticmethod
    def _prompt(
        definition: type[Prompt],
        primitive: CompiledPrimitive,
        metadata: dict[str, object],
    ) -> CompiledPrimitive:
        """Compile only explicitly named prompt arguments."""
        arguments = tuple(definition.arguments)
        names = tuple(item.name for item in arguments)
        if len(set(names)) != len(names) or any(not name for name in names):
            message = "Prompt argument names must be nonempty and unique."
            raise ValueError(message)
        metadata["arguments"] = arguments
        return replace(
            primitive,
            prompt_arguments=arguments,
            handler=McpInvoker.compile(definition, "handle", argument_names=names),
        )

    def synthetic(
        self, name: str, kind: Literal["search", "execute"], catalog: int,
    ) -> CompiledPrimitive:
        """Describe runtime-owned catalog operations using native typed schemas."""
        if not _NAME.fullmatch(name):
            message = "Invalid synthetic catalog tool name."
            raise ValueError(message)
        input_type = _SearchPayload if kind == "search" else _ExecutePayload
        schema = self.schema(input_type, input_schema=True)
        metadata = {
            "name": name,
            "description": (
                "Search available catalog tools and their complete input schemas."
                if kind == "search"
                else "Execute catalog tools in order; stop on the first error."
            ),
            "inputSchema": schema,
        }
        return CompiledPrimitive(
            definition=Tool,
            name=name,
            metadata=_wire(metadata),
            handler=None,
            input_type=input_type,
            input_schema=_wire(schema),
            synthetic=kind,
            catalog=catalog,
            cache=self.cache,
        )


def _insert(
    registry: dict[str, CompiledPrimitive], key: str, primitive: CompiledPrimitive,
) -> None:
    """Reject collisions at boot instead of changing lookup semantics silently."""
    if key in registry:
        message = f"Duplicate MCP primitive identifier {key!r}."
        raise ValueError(message)
    registry[key] = primitive


def _extensions(definition: type[Server]) -> tuple[McpExtension, ...]:
    """Reject extension collisions with built-in methods and other extensions."""
    extensions = tuple(definition.extensions)
    identifiers: set[str] = set()
    methods = set(_CORE_METHODS)
    for extension in extensions:
        if (
            not isinstance(extension, McpExtension)
            or extension.identifier in identifiers
        ):
            message = "Server extensions must be unique McpExtension declarations."
            raise ValueError(message)
        identifiers.add(extension.identifier)
        if methods.intersection(extension.methods):
            message = "An extension method collides with an existing MCP method."
            raise ValueError(message)
        if set(extension.decoders) != set(extension.methods):
            message = "Each extension method requires one explicit parameter decoder."
            raise ValueError(message)
        methods.update(extension.methods)
    return cast("tuple[McpExtension, ...]", extensions)


def _ordered(registry: dict[str, CompiledPrimitive]) -> dict[str, CompiledPrimitive]:
    """Keep deterministic name order in the compiled mapping, including URI keys."""
    return dict(sorted(registry.items(), key=lambda item: item[1].name))


def _tool_registry(
    compiler: _Compiler,
    entries: tuple[object, ...],
) -> tuple[
    dict[str, CompiledPrimitive],
    dict[str, CompiledPrimitive],
    tuple[CompiledCatalog, ...],
]:
    """Compile visible and hidden tool namespaces with collision checks."""
    tools: dict[str, CompiledPrimitive] = {}
    hidden: dict[str, CompiledPrimitive] = {}
    catalogs: list[CompiledCatalog] = []
    for entry in entries:
        if isinstance(entry, ToolCatalog):
            catalog_tools: dict[str, CompiledPrimitive] = {}
            for tool in entry.tools:
                primitive = compiler.primitive(tool, Tool)
                _insert(catalog_tools, primitive.name, primitive)
                _insert(hidden, primitive.name, primitive)
            operations: tuple[tuple[str, Literal["search", "execute"]], ...] = (
                (entry.search_name, "search"),
                (entry.execute_name, "execute"),
            )
            for name, kind in operations:
                _insert(tools, name, compiler.synthetic(name, kind, len(catalogs)))
            catalogs.append(
                CompiledCatalog(
                    tools=MappingProxyType(_ordered(catalog_tools)),
                    search_name=entry.search_name,
                    execute_name=entry.execute_name,
                    index=tuple(
                        (item.name, item.search_text)
                        for item in _ordered(catalog_tools).values()
                    ),
                ),
            )
        else:
            primitive = compiler.primitive(cast("type[Tool]", entry), Tool)
            _insert(tools, primitive.name, primitive)
    if set(tools).intersection(hidden):
        message = "Visible, catalog and synthetic tool names must not collide."
        raise ValueError(message)
    return _ordered(tools), _ordered(hidden), tuple(catalogs)


def _resource_registry(
    compiler: _Compiler,
    entries: tuple[type[Resource], ...],
) -> tuple[dict[str, CompiledPrimitive], tuple[CompiledPrimitive, ...]]:
    """Reject identical URI/template names and automatically detectable ambiguity."""
    resources: dict[str, CompiledPrimitive] = {}
    templates: dict[str, CompiledPrimitive] = {}
    names: set[str] = set()
    patterns: set[str] = set()
    for item in entries:
        primitive = compiler.primitive(item, Resource)
        if primitive.name in names:
            message = "Exact resources and templates must have unique names."
            raise ValueError(message)
        names.add(primitive.name)
        if primitive.matcher is None:
            _insert(resources, cast("str", primitive.uri), primitive)
        else:
            pattern = primitive.matcher.pattern
            if pattern is not None and primitive.matcher.custom is None:
                if pattern.pattern in patterns:
                    message = "Resource templates have identical inverse patterns."
                    raise ValueError(message)
                patterns.add(pattern.pattern)
            _insert(templates, primitive.matcher.template, primitive)
    return _ordered(resources), tuple(_ordered(templates).values())


def _capabilities(
    definition: type[Server],
    tools: Mapping[str, CompiledPrimitive],
    resources: Mapping[str, CompiledPrimitive],
    prompts: Mapping[str, CompiledPrimitive],
    templates: tuple[CompiledPrimitive, ...],
) -> dict[str, object]:
    """Advertise only the methods and notifications backed by this registry."""
    extensions = cast("tuple[McpExtension, ...]", definition.extensions)
    capabilities: dict[str, object] = {}
    for key, collection in (
        ("tools", tools),
        ("resources", resources or templates),
        ("prompts", prompts),
    ):
        if collection:
            capabilities[key] = {"listChanged": definition.list_changed}
    if resources or templates:
        resource_capability = cast("dict[str, object]", capabilities["resources"])
        resource_capability["subscribe"] = definition.resource_subscriptions
    if any(
        item.completion is not None
        for item in (*resources.values(), *templates, *prompts.values())
    ):
        capabilities["completions"] = {}
    if extensions:
        capabilities["extensions"] = {
            item.identifier: mutable_json(item.capabilities) for item in extensions
        }
    return capabilities


def compile_server(definition: type[Server]) -> CompiledMcpServer:
    """Compile one definition without resolving services or retaining runtime state."""
    if not isinstance(definition, type) or not issubclass(definition, Server):
        message = "MCP servers must be Server subclasses."
        raise TypeError(message)
    if not definition.name or not definition.version:
        message = "MCP servers must declare a nonempty name and version."
        raise ValueError(message)
    if not isinstance(definition.cache, CacheHint) or any(
        type(flag) is not bool
        for flag in (definition.list_changed, definition.resource_subscriptions)
    ) or not isinstance(definition.instructions, str):
        message = "Invalid MCP server cache, capability flags or instructions."
        raise TypeError(message)
    info = msgspec.convert(msgspec.to_builtins(ServerInfo(
        name=definition.name,
        version=definition.version,
        title=definition.title or msgspec.UNSET,
        description=definition.description or msgspec.UNSET,
        website_url=definition.website_url or msgspec.UNSET,
        icons=definition.icons or msgspec.UNSET,
    )), type=ServerInfo, strict=True)
    extensions = _extensions(definition)
    compiler = _Compiler(extensions, definition.cache)
    tools, hidden, catalogs = _tool_registry(compiler, definition.tools)
    resources, templates = _resource_registry(compiler, definition.resources)
    prompts: dict[str, CompiledPrimitive] = {}
    for item in definition.prompts:
        primitive = compiler.primitive(item, Prompt)
        _insert(prompts, primitive.name, primitive)
    capabilities = _capabilities(definition, tools, resources, prompts, templates)
    return CompiledMcpServer(
        definition=definition,
        tools=MappingProxyType(tools),
        resources=MappingProxyType(resources),
        prompts=MappingProxyType(_ordered(prompts)),
        templates=templates,
        info=info,
        capabilities=cast("Mapping[str, object]", freeze_json(capabilities)),
        capabilities_wire=_wire(capabilities),
        instructions=definition.instructions,
        cache=definition.cache,
        extensions=extensions,
        catalog_tools=MappingProxyType(hidden),
        catalogs=catalogs,
    )


def validate_payload(primitive: CompiledPrimitive, arguments: object) -> object:
    """Validate only the tool's argument object, never the HTTP JSON-RPC envelope."""
    payload = mutable_json(arguments)
    if not isinstance(payload, dict):
        message = "Tool arguments must be an object."
        raise msgspec.ValidationError(message)
    if primitive.input_type is None:
        if payload:
            message = "This tool does not accept arguments."
            raise msgspec.ValidationError(message)
        return msgspec.UNSET
    return convert_payload(payload, primitive.input_type)


def validate_output(primitive: CompiledPrimitive, value: object) -> object:
    """Enforce the advertised native output type before encoding structured data."""
    if primitive.output_type is msgspec.UNSET:
        return value
    if value is msgspec.UNSET:
        message = (
            "The tool declares an output schema but returned no structured content."
        )
        raise msgspec.ValidationError(message)
    return convert_payload(value, primitive.output_type)


def validate_prompt_arguments(
    primitive: CompiledPrimitive, arguments: Mapping[str, object],
) -> None:
    """Check required/unknown argument names and the protocol's string values."""
    names = {item.name for item in primitive.prompt_arguments}
    if set(arguments) - names or any(
        not isinstance(value, str) for value in arguments.values()
    ):
        message = "Invalid prompt arguments"
        raise McpInvalidParams(message)
    if any(
        item.required and item.name not in arguments
        for item in primitive.prompt_arguments
    ):
        message = "Missing required prompt arguments"
        raise McpInvalidParams(message)
