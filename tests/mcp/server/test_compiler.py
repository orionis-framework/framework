"""Verify schema, registry and catalog guarantees before runtime integration."""

# Native schema and DI annotations are evaluated at runtime during compilation.
# ruff: noqa: TC001

import unittest
from dataclasses import FrozenInstanceError

import msgspec

from orionis.mcp.context import McpRequest
from orionis.mcp.exceptions import McpInvalidParams
from orionis.mcp.protocol.metadata import CacheHint, PromptArgument, ToolAnnotations
from orionis.mcp.server.catalog import ToolCatalog
from orionis.mcp.server.compiler import (
    compile_server,
    validate_output,
    validate_payload,
    validate_prompt_arguments,
)
from orionis.mcp.server.extension import McpExtension
from orionis.mcp.server.primitives import Prompt, Resource, Server, Tool
from orionis.schemas import Schema
from orionis.schemas.constraints import MinLength
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Description, ExtraJsonSchema
from orionis.schemas.exceptions.validation import ValidationException


class WeatherInput(Schema):
    """Reuse Orionis documentation, constraints and field metadata."""

    location: Field[str, MinLength(2), Description("City name")]
    region: Field[str, ExtraJsonSchema({"x-mcp-header": "Region"})] = "us"


class CurrentWeatherTool(Tool[WeatherInput, list[int]]):
    """Infer typed input and scalar-array output from generic parameters."""

    annotations = ToolAnnotations(read_only=True, destructive=False)

    def handle(self, payload: WeatherInput) -> list[int]:
        """Return predictable structured data for this fixture."""
        return [len(payload.location)]


class StatusResource(Resource):
    """A literal URI independent of any filesystem."""

    uri = "demo://status"

    def handle(self) -> str:
        """Return a small text resource."""
        return "ready"


class ExplainPrompt(Prompt):
    """A string argument safe to bind by its explicitly declared name."""

    arguments = (PromptArgument(name="topic", required=True),)

    def handle(self, topic: str) -> str:
        """Return the validated prompt value."""
        return topic

    def complete(self, request: McpRequest) -> list[str]:
        """Expose completion only because a real provider exists."""
        return [request.method]


class DemoServer(Server):
    """A complete minimal declaration."""

    name = "Weather"
    tools = (CurrentWeatherTool,)
    resources = (StatusResource,)
    prompts = (ExplainPrompt,)


class TestCompiledServer(unittest.TestCase):
    """Compile definitions without resolving any application service."""

    def test_native_schema_and_metadata(self):
        """Keep native constraints, descriptions and compiled header bindings."""
        compiled = compile_server(DemoServer)
        tool = compiled.tools["current-weather"]
        metadata = msgspec.json.decode(tool.metadata)
        self.assertEqual(metadata["inputSchema"]["type"], "object")
        self.assertEqual(
            metadata["inputSchema"]["properties"]["location"]["minLength"], 2,
        )
        self.assertEqual(
            metadata["inputSchema"]["properties"]["location"]["description"],
            "City name",
        )
        self.assertEqual(metadata["annotations"]["readOnlyHint"], True)
        self.assertEqual(tool.mirrored_headers[0].name, "mcp-param-region")
        self.assertEqual(metadata["outputSchema"]["type"], "array")
        self.assertIn("completions", compiled.capabilities)

    def test_native_validation_and_output(self):
        """Validate constraints and reject output that violates the advertised type."""
        tool = compile_server(DemoServer).tools["current-weather"]
        self.assertEqual(
            validate_payload(tool, {"location": "Bogota"}).location, "Bogota",
        )
        with self.assertRaises(ValidationException):
            validate_payload(tool, {"location": "x"})
        with self.assertRaises(msgspec.ValidationError):
            validate_output(tool, ["wrong"])
        self.assertEqual(validate_output(tool, [1, 2]), [1, 2])

    def test_immutable_snapshot(self):
        """Compiled metadata and registries cannot be mutated between callers."""
        compiled = compile_server(DemoServer)
        with self.assertRaises(TypeError):
            compiled.tools["new"] = compiled.tools["current-weather"]
        with self.assertRaises(TypeError):
            compiled.capabilities["tools"]["listChanged"] = True
        with self.assertRaises(FrozenInstanceError):
            compiled.instructions = "changed"

    def test_duplicates_fail_at_boot(self):
        """Never silently overwrite tools or URI registrations."""
        for field, entries in (
            ("tools", (CurrentWeatherTool, CurrentWeatherTool)),
            ("resources", (StatusResource, StatusResource)),
        ):
            definition = type("Duplicates", (DemoServer,), {field: entries})
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_server(definition)

    def test_catalog_is_hidden_and_indexed(self):
        """Advertise synthetic operations without leaking all catalog schemas."""
        definition = type(
            "Catalog",
            (Server,),
            {
                "name": "Catalog",
                "tools": (ToolCatalog(CurrentWeatherTool),),
            },
        )
        compiled = compile_server(definition)
        self.assertEqual(tuple(compiled.tools), ("execute_tools", "search_tools"))
        self.assertIn("current-weather", compiled.catalog_tools)
        self.assertIn("city name", compiled.catalogs[0].index[0][1])
        self.assertEqual(compiled.tools["execute_tools"].synthetic, "execute")

    def test_catalog_collision_fails(self):
        """Hidden tools cannot collide with ordinary or synthetic tool names."""
        definition = type(
            "Collision",
            (DemoServer,),
            {
                "tools": (CurrentWeatherTool, ToolCatalog(CurrentWeatherTool)),
            },
        )
        with self.assertRaises(ValueError):
            compile_server(definition)

    def test_prompt_required_and_string_arguments(self):
        """Prompt strings and argument names are validated independently of DI."""
        prompt = compile_server(DemoServer).prompts["explain"]
        for values in ({}, {"topic": 1}, {"topic": "x", "service": "bad"}):
            with self.subTest(values=values), self.assertRaises(McpInvalidParams):
                validate_prompt_arguments(prompt, values)
        validate_prompt_arguments(prompt, {"topic": "weather"})

    def test_empty_server_omits_capabilities(self):
        """Do not advertise absent completion or primitive implementations."""
        definition = type("Empty", (Server,), {"name": "Empty"})
        self.assertEqual(dict(compile_server(definition).capabilities), {})

    def test_unsupported_extra_validation_is_rejected(self):
        """Do not advertise JSON Schema constraints that msgspec cannot enforce."""

        class Unsupported(Schema):
            value: Field[str, ExtraJsonSchema({"const": "only"})]

        definition = type("Unvalidated", (CurrentWeatherTool,), {"input": Unsupported})
        server = type("BadSchema", (Server,), {"name": "Bad", "tools": (definition,)})
        with self.assertRaisesRegex(ValueError, "not enforced"):
            compile_server(server)

    def test_recursive_schema_preserves_definitions(self):
        """Keep local references intact when making the input root an object."""

        class Node(msgspec.Struct):
            name: str
            children: list[Node] = msgspec.field(default_factory=list)

        class TreeTool(Tool[Node]):
            def handle(self, request: McpRequest) -> str:
                """Read explicit context without a payload annotation."""
                return request.method

        server = type("Recursive", (Server,), {"name": "Tree", "tools": (TreeTool,)})
        schema = msgspec.json.decode(compile_server(server).tools["tree"].input_schema)
        self.assertEqual(schema["type"], "object")
        self.assertIn("Node", schema["$defs"])

    def test_noarg_tool_rejects_payload(self):
        """The advertised empty object schema is enforced at runtime."""

        class EmptyTool(Tool):
            def handle(self) -> None:
                """Accept no client arguments."""

        server = type("Empty", (Server,), {"name": "Empty", "tools": (EmptyTool,)})
        primitive = compile_server(server).tools["empty"]
        self.assertIs(validate_payload(primitive, {}), msgspec.UNSET)
        with self.assertRaises(msgspec.ValidationError):
            validate_payload(primitive, {"unexpected": True})

    def test_extensions_require_decoders_and_cannot_override_core(self):
        """Extension routing is explicit and collision checked before boot."""
        for method, decoders in (("tools/list", {}), ("example/echo", {})):
            extension = McpExtension(
                identifier="com.example/echo",
                methods={method: str},
                decoders=decoders,
            )
            server = type(
                "Extended", (Server,), {"name": "Ext", "extensions": (extension,)},
            )
            with self.assertRaises(ValueError):
                compile_server(server)

    def test_cache_hint_validation(self):
        """A boolean or negative TTL cannot reach protocol output."""
        for ttl in (-1, True):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                CacheHint(ttl_ms=ttl)

    def test_static_metadata_and_extension_schema_integrity(self):
        """Fail boot when declarations or extension hooks break native contracts."""
        bad_tool = type("Bad", (CurrentWeatherTool,), {"description": 42})
        bad_server = type("BadServer", (Server,), {"name": "Bad", "tools": (bad_tool,)})
        with self.assertRaises(msgspec.ValidationError):
            compile_server(bad_server)

        def alter_schema(metadata):
            metadata["inputSchema"]["additionalProperties"] = False

        extension = McpExtension(
            identifier="org.example/test", schema_hook=alter_schema,
        )
        modified = type("Changed", (DemoServer,), {"extensions": (extension,)})
        with self.assertRaisesRegex(ValueError, "compiled standard field"):
            compile_server(modified)

        def annotate(metadata):
            metadata["_meta"] = {"org.example/test": {"view": "compact"}}

        extended = type("Extended", (DemoServer,), {"extensions": (
            McpExtension(identifier="org.example/test", schema_hook=annotate),
        )})
        primitive = compile_server(extended).tools["current-weather"]
        self.assertEqual(msgspec.json.decode(primitive.metadata)["_meta"], {
            "org.example/test": {"view": "compact"},
        })

    def test_inherited_generic_and_cache_policy(self):
        """A subclass keeps its generic payload and inherits its server's cache hint."""
        inherited = type("HistoricalWeatherTool", (CurrentWeatherTool,), {})
        hint = CacheHint(ttl_ms=1000, scope="public")
        server = type(
            "Inherited",
            (Server,),
            {
                "name": "Inherited",
                "tools": (inherited,),
                "cache": hint,
            },
        )
        primitive = compile_server(server).tools["historical-weather"]
        self.assertIs(primitive.input_type, WeatherInput)
        self.assertEqual(primitive.output_type, list[int])
        self.assertIs(primitive.cache, hint)
