# ruff: noqa: TC003
# Keep public compiled metadata and iterator annotations resolvable at runtime.
"""Provide mcp server operations.

Includes ``CompiledPrimitive``, ``CompiledCatalog``, ``CompiledMcpServer``,
``compile_server``.
"""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType, get_original_bases
from typing import Annotated, Literal, get_args, get_origin, cast
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
from orionis.mcp.protocol.validation import validate_json
from orionis.mcp.server.catalog import ToolCatalog
from orionis.mcp.server.extension import McpExtension
from orionis.mcp.server.primitives import Primitive, Prompt, Resource, Server, Tool
from orionis.mcp.server.schemas import (
    _ConversionPlan,
    compile_conversion,
    compile_schema,
    convert_payload,
)
from orionis.mcp.server.templates import UriMatcher, validate_uri
from orionis.mcp.transport.headers import HeaderBinding, compile_header_bindings

type _JsonObject = dict[str, object]
"""Type alias for ``dict[str, object]``."""

_NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}")
"""Compiled pattern used to recognize name."""
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
"""Core methods used by ``compiler``."""


class _SearchPayload(msgspec.Struct, forbid_unknown_fields=True):
    """Bounded searchable catalog arguments."""

    query: Annotated[str, msgspec.Meta(max_length=4096)] = ""
    """Query identifier: ``''``."""
    limit: Annotated[int, msgspec.Meta(ge=1, le=100)] = 10
    """Limit value used by ``_SearchPayload``."""


class _CatalogCall(msgspec.Struct, forbid_unknown_fields=True):
    """An independent catalog invocation, with no Python call kwargs."""

    name: str
    """Name identifying this declaration within its containing registry."""
    arguments: dict[str, object] = msgspec.field(default_factory=dict)
    """Command-line argument declarations accepted by this command."""


class _ExecutePayload(msgspec.Struct, forbid_unknown_fields=True):
    """Request limits are additionally enforced by the dispatcher configuration."""

    calls: Annotated[list[_CatalogCall], msgspec.Meta(min_length=1)]
    """Tool invocations included in the catalog execution request."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompiledPrimitive:
    """Unbound declaration metadata, with no identity or per-call service instance."""

    definition: type[Primitive]
    """Original declaration from which runtime metadata was compiled."""
    name: str
    """Name identifying this declaration within its containing registry."""
    metadata: msgspec.Raw
    """Compiled metadata used to describe and invoke the registered operation."""
    handler: McpInvoker | None
    """Callable or method selected to handle the registered operation."""
    description: str = ""
    """Description identifier: ``''``."""
    availability: McpInvoker | None = None
    """Hook determining whether the primitive is visible for this request."""
    authorization: McpInvoker | None = None
    """Hook deciding whether the current caller may invoke the primitive."""
    completion: McpInvoker | None = None
    """Completion provider or result associated with the primitive."""
    input_type: object = None
    """Python schema type used to decode and validate handler input."""
    output_type: object = msgspec.UNSET
    input_schema: msgspec.Raw | None = None
    """JSON Schema describing the accepted input."""
    output_schema: msgspec.Raw | None = None
    """JSON Schema describing the declared structured output."""
    input_plan: _ConversionPlan | None = None
    """Prepared input conversion and nested rule metadata."""
    output_plan: _ConversionPlan | None = None
    """Prepared output conversion and nested rule metadata."""
    mirrored_headers: tuple[HeaderBinding, ...] = ()
    """HTTP-header bindings derived from the primitive input schema."""
    cache: CacheHint = field(default_factory=CacheHint)
    """Cache policy or cached state used by this component."""
    uri: str | None = None
    """Resource URI identifying the requested or returned content."""
    mime_type: str | None = None
    """Media type describing the resource content."""
    prompt_arguments: tuple[PromptArgument, ...] = ()
    """Argument declarations accepted by the prompt."""
    matcher: UriMatcher | None = None
    """Compiled matcher resolving parameters from a resource URI."""
    synthetic: Literal["search", "execute"] | None = None
    """Whether this primitive was generated for catalog dispatch."""
    catalog: int | None = None
    """Catalog metadata associated with this primitive."""
    search_text: str = ""
    """Search text identifier: ``''``."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompiledCatalog:
    """One hidden catalog and its deterministic boot-time lexical index."""

    tools: Mapping[str, CompiledPrimitive]
    """Tool declarations available through this server or catalog."""
    search_name: str
    """Public tool name used to search the catalog."""
    execute_name: str
    """Public tool name used to execute catalog calls."""
    index: tuple[tuple[str, str], ...]
    """Lookup index used to resolve registered entries."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CompiledMcpServer:
    """A definition reusable by every request, worker and supported transport."""

    definition: type[Server]
    """Original declaration from which runtime metadata was compiled."""
    tools: Mapping[str, CompiledPrimitive]
    """Tool declarations available through this server or catalog."""
    resources: Mapping[str, CompiledPrimitive]
    """Resource declarations available through this server."""
    prompts: Mapping[str, CompiledPrimitive]
    """Prompt declarations available through this server."""
    templates: tuple[CompiledPrimitive, ...]
    """Compiled resource templates indexed by their identifiers."""
    info: ServerInfo
    """Server identity metadata exposed during discovery."""
    capabilities: Mapping[str, object]
    """Capabilities advertised by the compiled server."""
    capabilities_wire: msgspec.Raw
    """Preencoded capabilities retained for protocol responses."""
    instructions: str
    """Instructions exposed by the server to protocol clients."""
    cache: CacheHint
    """Cache policy or cached state used by this component."""
    extensions: tuple[McpExtension, ...]
    """Extensions registered for this server or transport."""
    catalog_tools: Mapping[str, CompiledPrimitive]
    """Tools belonging to compiled catalogs."""
    catalogs: tuple[CompiledCatalog, ...]
    """Catalogs compiled for this server."""


def _wire(value: object) -> msgspec.Raw:
    """
    Freeze wire metadata into immutable JSON without retaining mutable maps.

    Parameters
    ----------
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    ``msgspec.Raw``
        Result of the operation described above.
    """
    return msgspec.Raw(msgspec.json.encode(value))


def _validate_static_metadata(metadata: dict[str, object], kind: type) -> None:
    """
    Check declaration constructors once, keeping validation off list hot paths.

    Parameters
    ----------
    metadata : dict[str, object]
        Metadata associated with the current operation.
    kind : type
        Value supplied for ``kind``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    expected = {Tool: ToolMetadata, Resource: ResourceMetadata, Prompt: PromptMetadata}
    msgspec.convert(msgspec.to_builtins(metadata), type=expected[kind], strict=True)
    if "_meta" in metadata:
        validate_metadata(metadata["_meta"], allow_reserved=False)
        validate_json(metadata["_meta"])


def _extend_metadata(
    metadata: dict[str, object],
    extensions: tuple[McpExtension, ...],
) -> dict[str, object]:
    """
    Let extensions attach data without changing compiled native contracts.

    Parameters
    ----------
    metadata : dict[str, object]
        Metadata associated with the current operation.
    extensions : tuple[orionis.mcp.McpExtension, ``...``]
        Value supplied for ``extensions``.

    Returns
    -------
    dict[str, object]
        Result of the operation described above.
    """
    if not extensions:
        return metadata
    baseline = cast("_JsonObject", mutable_json(metadata))
    extended = cast("_JsonObject", mutable_json(baseline))
    for extension in extensions:
        if extension.schema_hook is not None:
            extension.schema_hook(extended)
    for key in (
        "name",
        "title",
        "description",
        "icons",
        "annotations",
        "inputSchema",
        "outputSchema",
        "uri",
        "uriTemplate",
        "mimeType",
        "size",
        "arguments",
    ):
        if extended.get(key, msgspec.UNSET) != baseline.get(key, msgspec.UNSET):
            message = (
                "Extension schema hooks may attach extension metadata but cannot "
                f"change compiled standard field {key!r}."
            )
            raise ValueError(message)
    return extended


def _name(definition: type[Primitive]) -> str:
    """
    Derive readable kebab names while honoring explicit protocol identifiers.

    Parameters
    ----------
    definition : type[orionis.mcp.server.primitives.Primitive]
        Class declaration whose metadata is being inspected.

    Returns
    -------
    str
        Result of the operation described above.
    """
    if definition.name:
        name = definition.name
    else:
        stem = definition.__name__
        for suffix in ("Tool", "Resource", "Prompt"):
            if stem.endswith(suffix):
                stem = stem.removesuffix(suffix)
                break
        stem = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "-", stem)
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", stem).replace("_", "-").lower()
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        message = f"Invalid MCP primitive name {name!r}."
        raise ValueError(message)
    return name


def _metadata(definition: type[Primitive], name: str) -> dict[str, object]:
    """
    Snapshot common metadata before adding primitive-specific wire fields.

    Parameters
    ----------
    definition : type[orionis.mcp.server.primitives.Primitive]
        Class declaration whose metadata is being inspected.
    name : str
        Value supplied for ``name``.

    Returns
    -------
    dict[str, object]
        Result of the operation described above.
    """
    metadata: dict[str, object] = {"name": name}
    for key in ("title", "description", "icons"):
        value = getattr(definition, key)
        if value:
            metadata[key] = value
    if definition.meta:
        metadata["_meta"] = mutable_json(definition.meta)
    return metadata


def _hook(definition: type, method: str) -> McpInvoker | None:
    """
    Compile optional per-request checks without resolving a handler instance.

    Parameters
    ----------
    definition : type
        Class declaration whose metadata is being inspected.
    method : str
        Value supplied for ``method``.

    Returns
    -------
    orionis.mcp.invoker.McpInvoker | None
        Result of the operation described above.
    """
    return (
        McpInvoker.compile(definition, method) if hasattr(definition, method) else None
    )


def _tool_arguments(definition: type[Tool]) -> Iterator[tuple[object, ...]]:
    """
    Enumerate generic Tool arguments in method resolution order.

    Parameters
    ----------
    definition : type[orionis.mcp.Tool]
        Tool declaration whose generic bases are inspected.

    Yields
    ------
    tuple[object, ``...``]
        Input and output declarations from each Tool generic base.
    """
    for ancestor in definition.__mro__:
        for base in get_original_bases(ancestor):
            if get_origin(base) is Tool:
                yield get_args(base)


def _tool_types(definition: type[Tool]) -> tuple[object, object]:
    """
    Resolve explicit or generic input and output declarations.

    Parameters
    ----------
    definition : type[orionis.mcp.Tool]
        Tool class carrying explicit fields or inherited generic arguments.

    Returns
    -------
    tuple[object, object]
        Input type and output type, with UNSET for an undeclared output.
    """
    input_type = definition.input
    output_type = definition.output
    for arguments in _tool_arguments(definition):
        if input_type is None and arguments and arguments[0] is not object:
            input_type = arguments[0]
        if output_type is None and len(arguments) > 1 and arguments[1] is not object:
            output_type = arguments[1]
    return input_type, msgspec.UNSET if output_type is None else output_type


class _Compiler:
    """Own only boot-time schema caches; discard them after the registry is built."""

    __slots__ = ("cache", "extensions", "schemas")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, extensions: tuple[McpExtension, ...], cache: CacheHint) -> None:
        """
        Use a per-compilation cache rather than growing a process-global cache.

        Parameters
        ----------
        extensions : tuple[orionis.mcp.McpExtension, ``...``]
            Value supplied for ``extensions``.
        cache : orionis.mcp.CacheHint
            Value supplied for ``cache``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self.schemas: dict[tuple[object, bool], dict[str, object]] = {}
        """Schema definitions collected during compilation."""
        self.extensions = extensions
        """Value supplied for ``extensions``."""
        self.cache = cache
        """Value supplied for ``cache``."""

    def schema(self, annotation: object, *, input_schema: bool) -> dict[str, object]:
        """
        Share one schema snapshot per type and direction inside this compilation.

        Parameters
        ----------
        annotation : object
            Native type annotation to inspect or validate.
        input_schema : bool
            Value supplied for ``input_schema``.

        Returns
        -------
        dict[str, object]
            Result of the operation described above.
        """
        key = (annotation, input_schema)
        if key not in self.schemas:
            self.schemas[key] = compile_schema(annotation, input_schema=input_schema)
        return self.schemas[key]

    def primitive(
        self,
        definition: type[Primitive],
        kind: type[Primitive],
    ) -> CompiledPrimitive:
        """
        Compile one ordinary primitive and all of its immutable handler plans.

        Parameters
        ----------
        definition : type[orionis.mcp.server.primitives.Primitive]
            Class declaration whose metadata is being inspected.
        kind : type[orionis.mcp.server.primitives.Primitive]
            Value supplied for ``kind``.

        Returns
        -------
        orionis.mcp.server.compiler.CompiledPrimitive
            Result of the operation described above.
        """
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
                cast("type[Resource]", definition),
                primitive,
                metadata,
            )
        else:
            primitive = self._prompt(
                cast("type[Prompt]", definition),
                primitive,
                metadata,
            )
        metadata = _extend_metadata(metadata, self.extensions)
        _validate_static_metadata(metadata, kind)
        return cast(
            "CompiledPrimitive",
            replace(
                primitive,
                metadata=_wire(metadata),
                search_text=msgspec.json.encode(metadata).decode("utf-8").lower(),
            ),
        )

    def _tool(
        self,
        definition: type[Tool],
        primitive: CompiledPrimitive,
        metadata: dict[str, object],
    ) -> CompiledPrimitive:
        """
        Compile typed tool schemas and statically reachable header bindings.

        Parameters
        ----------
        definition : type[orionis.mcp.Tool]
            Class declaration whose metadata is being inspected.
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Compiled tool, resource or prompt declaration.
        metadata : dict[str, object]
            Metadata associated with the current operation.

        Returns
        -------
        orionis.mcp.server.compiler.CompiledPrimitive
            Result of the operation described above.
        """
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
        return cast(
            "CompiledPrimitive",
            replace(
                primitive,
                input_type=input_type,
                output_type=output_type,
                input_schema=_wire(schema),
                output_schema=_wire(output_schema)
                if output_schema is not None
                else None,
                input_plan=(
                    compile_conversion(input_type) if input_type is not None else None
                ),
                output_plan=(
                    compile_conversion(output_type)
                    if output_type is not msgspec.UNSET
                    else None
                ),
                mirrored_headers=compile_header_bindings(schema),
                handler=McpInvoker.compile(definition, "handle", input_type),
            ),
        )

    @staticmethod
    def _resource(
        definition: type[Resource],
        primitive: CompiledPrimitive,
        metadata: dict[str, object],
    ) -> CompiledPrimitive:
        """
        Compile exact resources and RFC templates with safe inverse matching.

        Parameters
        ----------
        definition : type[orionis.mcp.Resource]
            Class declaration whose metadata is being inspected.
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Compiled tool, resource or prompt declaration.
        metadata : dict[str, object]
            Metadata associated with the current operation.

        Returns
        -------
        orionis.mcp.server.compiler.CompiledPrimitive
            Result of the operation described above.
        """
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
        return cast(
            "CompiledPrimitive",
            replace(
                primitive,
                matcher=matcher,
                uri=definition.uri or definition.uri_template,
                mime_type=definition.mime_type,
                handler=McpInvoker.compile(definition, "handle", uri_names=uri_names),
            ),
        )

    @staticmethod
    def _prompt(
        definition: type[Prompt],
        primitive: CompiledPrimitive,
        metadata: dict[str, object],
    ) -> CompiledPrimitive:
        """
        Compile only explicitly named prompt arguments.

        Parameters
        ----------
        definition : type[orionis.mcp.Prompt]
            Class declaration whose metadata is being inspected.
        primitive : orionis.mcp.server.compiler.CompiledPrimitive
            Compiled tool, resource or prompt declaration.
        metadata : dict[str, object]
            Metadata associated with the current operation.

        Returns
        -------
        orionis.mcp.server.compiler.CompiledPrimitive
            Result of the operation described above.
        """
        arguments = tuple(definition.arguments)
        names = tuple(item.name for item in arguments)
        if len(set(names)) != len(names) or any(not name for name in names):
            message = "Prompt argument names must be nonempty and unique."
            raise ValueError(message)
        metadata["arguments"] = arguments
        return cast(
            "CompiledPrimitive",
            replace(
                primitive,
                prompt_arguments=arguments,
                handler=McpInvoker.compile(definition, "handle", argument_names=names),
            ),
        )

    def synthetic(
        self,
        name: str,
        kind: Literal["search", "execute"],
        catalog: int,
    ) -> CompiledPrimitive:
        """
        Describe runtime-owned catalog operations using native typed schemas.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.
        kind : typing.Literal['``search``', '``execute``']
            Value supplied for ``kind``.
        catalog : int
            Value supplied for ``catalog``.

        Returns
        -------
        orionis.mcp.server.compiler.CompiledPrimitive
            Result of the operation described above.
        """
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
    registry: dict[str, CompiledPrimitive],
    key: str,
    primitive: CompiledPrimitive,
) -> None:
    """
    Reject collisions at boot instead of changing lookup semantics silently.

    Parameters
    ----------
    registry : dict[str, orionis.mcp.server.compiler.CompiledPrimitive]
        Value supplied for ``registry``.
    key : str
        Value supplied for ``key``.
    primitive : orionis.mcp.server.compiler.CompiledPrimitive
        Compiled tool, resource or prompt declaration.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if key in registry:
        message = f"Duplicate MCP primitive identifier {key!r}."
        raise ValueError(message)
    registry[key] = primitive


def _extensions(definition: type[Server]) -> tuple[McpExtension, ...]:
    """
    Reject extension collisions with built-in methods and other extensions.

    Parameters
    ----------
    definition : type[orionis.mcp.Server]
        Class declaration whose metadata is being inspected.

    Returns
    -------
    tuple[orionis.mcp.McpExtension, ``...``]
        Result of the operation described above.
    """
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
    """
    Keep deterministic name order in the compiled mapping, including URI keys.

    Parameters
    ----------
    registry : dict[str, orionis.mcp.server.compiler.CompiledPrimitive]
        Value supplied for ``registry``.

    Returns
    -------
    dict[str, orionis.mcp.server.compiler.CompiledPrimitive]
        Result of the operation described above.
    """
    return dict(sorted(registry.items(), key=lambda item: item[1].name))


def _tool_registry(
    compiler: _Compiler,
    entries: tuple[object, ...],
) -> tuple[
    dict[str, CompiledPrimitive],
    dict[str, CompiledPrimitive],
    tuple[CompiledCatalog, ...],
]:
    """
    Compile visible and hidden tool namespaces with collision checks.

    Parameters
    ----------
    compiler : orionis.mcp.server.compiler._Compiler
        Value supplied for ``compiler``.
    entries : tuple[object, ``...``]
        Value supplied for ``entries``.

    Returns
    -------
    tuple
        Result of the operation described above.
    """
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
    """
    Reject identical URI/template names and automatically detectable ambiguity.

    Parameters
    ----------
    compiler : orionis.mcp.server.compiler._Compiler
        Value supplied for ``compiler``.
    entries : tuple[type[orionis.mcp.Resource], ``...``]
        Value supplied for ``entries``.

    Returns
    -------
    tuple[dict[str, CompiledPrimitive], tuple[CompiledPrimitive, ``...``]]
        Result of the operation described above.
    """
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
    """
    Advertise only the methods and notifications backed by this registry.

    Parameters
    ----------
    definition : type[orionis.mcp.Server]
        Class declaration whose metadata is being inspected.
    tools : collections.abc.Mapping[str, orionis.mcp.server.compiler.CompiledPrimitive]
        Value supplied for ``tools``.
    resources : Mapping[str, CompiledPrimitive]
        Value supplied for ``resources``.
    prompts : Mapping[str, CompiledPrimitive]
        Value supplied for ``prompts``.
    templates : tuple[orionis.mcp.server.compiler.CompiledPrimitive, ``...``]
        Value supplied for ``templates``.

    Returns
    -------
    dict[str, object]
        Result of the operation described above.
    """
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
        resource_capability = cast("_JsonObject", capabilities["resources"])
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
    """
    Compile one definition without resolving services or retaining runtime state.

    Parameters
    ----------
    definition : type[orionis.mcp.Server]
        Class declaration whose metadata is being inspected.

    Returns
    -------
    orionis.mcp.server.compiler.CompiledMcpServer
        Result of the operation described above.
    """
    if not isinstance(definition, type) or not issubclass(definition, Server):
        message = "MCP servers must be Server subclasses."
        raise TypeError(message)
    if not definition.name or not definition.version:
        message = "MCP servers must declare a nonempty name and version."
        raise ValueError(message)
    if (
        not isinstance(definition.cache, CacheHint)
        or any(
            type(flag) is not bool
            for flag in (definition.list_changed, definition.resource_subscriptions)
        )
        or not isinstance(definition.instructions, str)
    ):
        message = "Invalid MCP server cache, capability flags or instructions."
        raise TypeError(message)
    info = msgspec.convert(
        msgspec.to_builtins(
            ServerInfo(
                name=definition.name,
                version=definition.version,
                title=definition.title or msgspec.UNSET,
                description=definition.description or msgspec.UNSET,
                website_url=definition.website_url or msgspec.UNSET,
                icons=definition.icons or msgspec.UNSET,
            ),
        ),
        type=ServerInfo,
        strict=True,
    )
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


async def validate_payload(primitive: CompiledPrimitive, arguments: object) -> object:
    """
    Validate only the tool's argument object, never the HTTP JSON-RPC envelope.

    Parameters
    ----------
    primitive : orionis.mcp.server.compiler.CompiledPrimitive
        Compiled tool, resource or prompt declaration.
    arguments : object
        Arguments supplied for this operation.

    Returns
    -------
    object
        Result of the operation described above.
    """
    payload = mutable_json(arguments)
    if not isinstance(payload, dict):
        message = "Tool arguments must be an object."
        raise msgspec.ValidationError(message)
    if primitive.input_type is None:
        if payload:
            message = "This tool does not accept arguments."
            raise msgspec.ValidationError(message)
        return msgspec.UNSET
    return await convert_payload(
        payload,
        primitive.input_type,
        plan=primitive.input_plan,
    )


async def validate_output(primitive: CompiledPrimitive, value: object) -> object:
    """
    Enforce the advertised native output type before encoding structured data.

    Parameters
    ----------
    primitive : orionis.mcp.server.compiler.CompiledPrimitive
        Compiled tool, resource or prompt declaration.
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    object
        Result of the operation described above.
    """
    if primitive.output_type is msgspec.UNSET:
        return value
    if value is msgspec.UNSET:
        message = (
            "The tool declares an output schema but returned no structured content."
        )
        raise msgspec.ValidationError(message)
    return await convert_payload(
        value,
        primitive.output_type,
        plan=primitive.output_plan,
    )


def validate_prompt_arguments(
    primitive: CompiledPrimitive,
    arguments: Mapping[str, object],
) -> None:
    """
    Check required/unknown argument names and the protocol's string values.

    Parameters
    ----------
    primitive : orionis.mcp.server.compiler.CompiledPrimitive
        Compiled tool, resource or prompt declaration.
    arguments : collections.abc.Mapping[str, object]
        Arguments supplied for this operation.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
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
