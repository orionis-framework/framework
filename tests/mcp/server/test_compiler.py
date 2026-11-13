# ruff: noqa: ANN001, ANN201, ANN202, PT009, PT027, TC001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Runtime schema and handler compilation require these concrete annotations.
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
from orionis.schemas.constraints import MinLength, StrongPassword
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Coerce, Description, ExtraJsonSchema
from orionis.test import TestCase


class WeatherInput(Schema):
    """Reuse Orionis documentation, constraints and field metadata."""

    location: Field[str, MinLength(2), Description("City name")]
    region: Field[str, ExtraJsonSchema({"x-mcp-header": "Region"})] = "us"


class CurrentWeatherTool(Tool[WeatherInput, list[int]]):
    """Infer typed input and scalar-array output from generic parameters."""

    annotations = ToolAnnotations(read_only=True, destructive=False)

    def handle(self, payload: WeatherInput) -> list[int]:
        """Return predictable structured data for this fixture.

        Parameters
        ----------
        payload : WeatherInput
            Value supplied for ``payload``.

        Returns
        -------
        list[int]
            Return the result produced by ``handle``.
        """
        return [len(payload.location)]


class StatusResource(Resource):
    """A literal URI independent of any filesystem."""

    uri = "demo://status"

    def handle(self) -> str:
        """Return a small text resource.

        Returns
        -------
        str
            Return the result produced by ``handle``.
        """
        return "ready"


class ExplainPrompt(Prompt):
    """A string argument safe to bind by its explicitly declared name."""

    arguments = (PromptArgument(name="topic", required=True),)

    def handle(self, topic: str) -> str:
        """Return the validated prompt value.

        Parameters
        ----------
        topic : str
            Value supplied for ``topic``.

        Returns
        -------
        str
            Return the result produced by ``handle``.
        """
        return topic

    def complete(self, request: McpRequest) -> list[str]:
        """Expose completion only because a real provider exists.

        Parameters
        ----------
        request : McpRequest
            Value supplied for ``request``.

        Returns
        -------
        list[str]
            Return the result produced by ``complete``.
        """
        return [request.method]


class DemoServer(Server):
    """A complete minimal declaration."""

    name = "Weather"
    tools = (CurrentWeatherTool,)
    resources = (StatusResource,)
    prompts = (ExplainPrompt,)


class _ValidatedValue(Schema):
    """Require marked conversion and a framework validation rule."""

    count: Field[int, Coerce()]
    password: Field[str, StrongPassword()]


class _WrappedInput(msgspec.Struct):
    """Carry framework schemas through an ordinary Struct input."""

    items: list[_ValidatedValue]


class _ValidatedTool(Tool[_WrappedInput]):
    """Declare a reusable conversion fixture without invoking services."""

    name = "validated"

    def handle(self, payload: _WrappedInput) -> object:
        """Return the already validated input.

        Parameters
        ----------
        payload : _WrappedInput
            Typed input owned by this invocation.

        Returns
        -------
        object
            The input wrapper.
        """
        return payload


class TestCompiledServer(TestCase):
    """Compile definitions without resolving any application service."""

    def testNativeSchemaAndMetadata(self):
        """Keep native constraints, descriptions and compiled header bindings.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        compiled = compile_server(DemoServer)
        tool = compiled.tools["current-weather"]
        metadata = msgspec.json.decode(tool.metadata)
        self.assertEqual(metadata["inputSchema"]["type"], "object")
        self.assertEqual(
            metadata["inputSchema"]["properties"]["location"]["minLength"],
            2,
        )
        self.assertEqual(
            metadata["inputSchema"]["properties"]["location"]["description"],
            "City name",
        )
        self.assertEqual(metadata["annotations"]["readOnlyHint"], True)  # NOSONAR
        self.assertEqual(tool.mirrored_headers[0].name, "mcp-param-region")
        self.assertEqual(metadata["outputSchema"]["type"], "array")
        self.assertIn("completions", compiled.capabilities)

    async def testNativeValidationAndOutput(self):
        """Validate constraints and reject output that violates the advertised type.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        tool = compile_server(DemoServer).tools["current-weather"]
        self.assertEqual(
            (await validate_payload(tool, {"location": "Bogota"})).location,
            "Bogota",
        )
        with self.assertRaises(ValidationException):
            await validate_payload(tool, {"location": "x"})
        with self.assertRaises(msgspec.ValidationError):
            await validate_output(tool, ["wrong"])
        self.assertEqual(await validate_output(tool, [1, 2]), [1, 2])

    async def testPlainStructInputsApplyNestedCoercionAndRules(self) -> None:
        """Validate schemas nested inside native Struct tool inputs.

        Returns
        -------
        None
            No return value.
        """
        server = type(
            "WrappedServer",
            (Server,),
            {"name": "Wrapped", "tools": (_ValidatedTool,)},
        )
        primitive = compile_server(server).tools["validated"]
        source = {"items": [{"count": "3", "password": "CorrectHorse9!Battery"}]}
        with self.subTest(check="coercion"):
            result = await validate_payload(primitive, source)
            self.assertIsInstance(result, _WrappedInput)
            self.assertEqual(result.items[0].count, 3)
            self.assertEqual(source["items"][0]["count"], "3")
        with self.subTest(check="custom rule"), self.assertRaises(ValidationException):
            await validate_payload(
                primitive,
                {"items": [{"count": 3, "password": "weak"}]},
            )

    async def testCompositeOutputsCannotBypassSchemaCoercionOrRules(self) -> None:
        """Enforce schema contracts through nullable and collection outputs.

        Returns
        -------
        None
            No return value.
        """
        valid = {"count": "3", "password": "CorrectHorse9!Battery"}
        invalid = {"count": 3, "password": "weak"}
        expected = _ValidatedValue(count=3, password=valid["password"])
        for annotation, value, bad_value, converted in (
            (_ValidatedValue | None, valid, invalid, expected),
            (list[_ValidatedValue], [valid], [invalid], [expected]),
            (
                dict[str, _ValidatedValue],
                {"first": valid},
                {"first": invalid},
                {"first": expected},
            ),
            (
                _WrappedInput,
                {"items": [valid]},
                {"items": [invalid]},
                _WrappedInput(items=[expected]),
            ),
        ):
            with self.subTest(annotation=annotation):
                tool = type("OutputTool", (_ValidatedTool,), {"output": annotation})
                server = type(
                    "OutputServer",
                    (Server,),
                    {"name": "Output", "tools": (tool,)},
                )
                primitive = compile_server(server).tools["validated"]
                with self.subTest(check="coercion"):
                    self.assertEqual(
                        await validate_output(primitive, value),
                        converted,
                    )
                with (
                    self.subTest(check="custom rule"),
                    self.assertRaises(ValidationException),
                ):
                    await validate_output(primitive, bad_value)
        self.assertEqual(valid["count"], "3")

    def testImmutableSnapshot(self):
        """Compiled metadata and registries cannot be mutated between callers.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        compiled = compile_server(DemoServer)
        with self.assertRaises(TypeError):
            compiled.tools["new"] = compiled.tools["current-weather"]
        with self.assertRaises(TypeError):
            compiled.capabilities["tools"]["listChanged"] = True
        with self.assertRaises(FrozenInstanceError):
            compiled.instructions = "changed"

    def testDuplicatesFailAtBoot(self):
        """Never silently overwrite tools or URI registrations.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for field, entries in (
            ("tools", (CurrentWeatherTool, CurrentWeatherTool)),
            ("resources", (StatusResource, StatusResource)),
        ):
            definition = type("Duplicates", (DemoServer,), {field: entries})
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_server(definition)

    def testCatalogIsHiddenAndIndexed(self):
        """Advertise synthetic operations without leaking all catalog schemas.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testCatalogCollisionFails(self):
        """Hidden tools cannot collide with ordinary or synthetic tool names.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        definition = type(
            "Collision",
            (DemoServer,),
            {
                "tools": (CurrentWeatherTool, ToolCatalog(CurrentWeatherTool)),
            },
        )
        with self.assertRaises(ValueError):
            compile_server(definition)

    def testPromptRequiredAndStringArguments(self):
        """Prompt strings and argument names are validated independently of DI.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        prompt = compile_server(DemoServer).prompts["explain"]
        for values in ({}, {"topic": 1}, {"topic": "x", "service": "bad"}):
            with self.subTest(values=values), self.assertRaises(McpInvalidParams):
                validate_prompt_arguments(prompt, values)
        validate_prompt_arguments(prompt, {"topic": "weather"})

    def testEmptyServerOmitsCapabilities(self):
        """Do not advertise absent completion or primitive implementations.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        definition = type("Empty", (Server,), {"name": "Empty"})
        self.assertEqual(dict(compile_server(definition).capabilities), {})

    def testUnsupportedExtraValidationIsRejected(self):
        """Do not advertise JSON Schema constraints that msgspec cannot enforce.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """

        class Unsupported(Schema):
            value: Field[str, ExtraJsonSchema({"const": "only"})]

        definition = type("Unvalidated", (CurrentWeatherTool,), {"input": Unsupported})
        server = type("BadSchema", (Server,), {"name": "Bad", "tools": (definition,)})
        with self.assertRaisesRegex(ValueError, "not enforced"):
            compile_server(server)

    def testRecursiveSchemaPreservesDefinitions(self):
        """Keep local references intact when making the input root an object.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """

        class Node(msgspec.Struct):
            name: str
            children: list[Node] = msgspec.field(default_factory=list)

        class TreeTool(Tool[Node]):
            def handle(self, request: McpRequest) -> str:
                """Read explicit context without a payload annotation.

                Parameters
                ----------
                request : McpRequest
                    Value supplied for ``request``.

                Returns
                -------
                str
                    Return the result produced by ``handle``.
                """
                return request.method

        server = type("Recursive", (Server,), {"name": "Tree", "tools": (TreeTool,)})
        schema = msgspec.json.decode(compile_server(server).tools["tree"].input_schema)
        self.assertEqual(schema["type"], "object")
        self.assertIn("Node", schema["$defs"])

    async def testNoargToolRejectsPayload(self):
        """The advertised empty object schema is enforced at runtime.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """

        class EmptyTool(Tool):
            def handle(self) -> None:
                """Accept no client arguments.

                Returns
                -------
                None
                    Complete the documented checks or setup without a return value.
                """

        server = type("Empty", (Server,), {"name": "Empty", "tools": (EmptyTool,)})
        primitive = compile_server(server).tools["empty"]
        self.assertIs(await validate_payload(primitive, {}), msgspec.UNSET)
        with self.assertRaises(msgspec.ValidationError):
            await validate_payload(primitive, {"unexpected": True})

    def testExtensionsRequireDecodersAndCannotOverrideCore(self):
        """Extension routing is explicit and collision checked before boot.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for method, decoders in (("tools/list", {}), ("example/echo", {})):
            extension = McpExtension(
                identifier="com.example/echo",
                methods={method: str},
                decoders=decoders,
            )
            server = type(
                "Extended",
                (Server,),
                {"name": "Ext", "extensions": (extension,)},
            )
            with self.assertRaises(ValueError):
                compile_server(server)

    def testCacheHintValidation(self):
        """A boolean or negative TTL cannot reach protocol output.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for ttl in (-1, True):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                CacheHint(ttl_ms=ttl)

    def testStaticMetadataAndExtensionSchemaIntegrity(self):
        """Fail boot when declarations or extension hooks break native contracts.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        bad_tool = type("Bad", (CurrentWeatherTool,), {"description": 42})
        bad_server = type("BadServer", (Server,), {"name": "Bad", "tools": (bad_tool,)})
        with self.assertRaises(msgspec.ValidationError):
            compile_server(bad_server)

        def alter_schema(metadata):
            """Attach the requested schema metadata.

            Parameters
            ----------
            metadata : object
                Value supplied for ``metadata``.

            Returns
            -------
            None
                Complete the documented checks or setup without a return value.
            """
            metadata["inputSchema"]["additionalProperties"] = False

        extension = McpExtension(
            identifier="org.example/test",
            schema_hook=alter_schema,
        )
        modified = type("Changed", (DemoServer,), {"extensions": (extension,)})
        with self.assertRaisesRegex(ValueError, "compiled standard field"):
            compile_server(modified)

        def annotate(metadata):
            """Apply the requested annotation to the schema.

            Parameters
            ----------
            metadata : object
                Value supplied for ``metadata``.

            Returns
            -------
            None
                Complete the documented checks or setup without a return value.
            """
            metadata["_meta"] = {"org.example/test": {"view": "compact"}}

        extended = type(
            "Extended",
            (DemoServer,),
            {
                "extensions": (
                    McpExtension(identifier="org.example/test", schema_hook=annotate),
                ),
            },
        )
        primitive = compile_server(extended).tools["current-weather"]
        self.assertEqual(
            msgspec.json.decode(primitive.metadata)["_meta"],
            {
                "org.example/test": {"view": "compact"},
            },
        )

    def testStaticMetadataRejectsNonfiniteValuesBeforeCompilation(self) -> None:
        """Reject static metadata that JSON encoding would silently turn into null.

        Returns
        -------
        None
            No return value.
        """
        for value in (float("nan"), float("inf"), float("-inf")):
            tool = type(
                "NonfiniteTool",
                (CurrentWeatherTool,),
                {"meta": {"example.org/value": {"nested": [value]}}},
            )
            server = type("NonfiniteServer", (DemoServer,), {"tools": (tool,)})
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "finite JSON",
                ),
            ):
                compile_server(server)

    def testInheritedGenericAndCachePolicy(self):
        """A subclass keeps its generic payload and inherits its server's cache hint.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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
