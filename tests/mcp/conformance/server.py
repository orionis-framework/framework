"""Diagnostic primitives required by the pinned official conformance referee.

These declarations are test fixtures only. Production AI routes never import them.
"""

import asyncio
import base64
from collections.abc import Mapping
import json
import struct

import msgspec

from orionis.mcp import (
    Completion,
    InputRequiredResult,
    McpRequest,
    McpResponse,
    McpState,
    Prompt,
    PromptArgument,
    Resource,
    Server,
    Tool,
)
from orionis.mcp.contracts.manager import IMcpManager  # noqa: TC001 - Native tool DI.

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aG3sAAAAASUVORK5CYII=",
)
WAV = (
    b"RIFF"
    + struct.pack("<I", 38)
    + b"WAVEfmt "
    + struct.pack(
        "<IHHIIHH",
        16,
        1,
        1,
        8000,
        16000,
        2,
        16,
    )
    + b"data"
    + struct.pack("<Ih", 2, 0)
)


def elicit(field="name", kind="string"):
    """Build a raw modern client input request, with no server RPC callback."""
    return {
        "method": "elicitation/create",
        "params": {
            "message": f"Provide {field}",
            "requestedSchema": {
                "type": "object",
                "properties": {field: {"type": kind}},
                "required": [field],
            },
        },
    }


def sample():
    """Ask the client for one bounded sampling result."""
    return {
        "method": "sampling/createMessage",
        "params": {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "What is the capital of France?",
                    },
                },
            ],
            "maxTokens": 100,
        },
    }


def accepted(request, key, field):
    """Validate an application-specific elicitation response."""
    value = request.input_responses.get(key)
    if not isinstance(value, Mapping) or value.get("action") != "accept":
        return None
    content = value.get("content")
    return content.get(field) if isinstance(content, Mapping) else None


class SimpleText(Tool):
    name = "test_simple_text"
    description = "Return diagnostic text."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.text("Hello from Orionis MCP conformance.")


class ImageTool(Tool):
    name = "test_image_content"
    description = "Return a one-pixel PNG."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.image(PNG, "image/png")


class AudioTool(Tool):
    name = "test_audio_content"
    description = "Return a minimal PCM WAV."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.audio(WAV, "audio/wav")


class EmbeddedTool(Tool):
    name = "test_embedded_resource"
    description = "Return embedded resource text."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.resource(
            "test://embedded-resource", "Embedded text", "text/plain",
        )


class MixedTool(Tool):
    name = "test_multiple_content_types"
    description = "Return text, image and embedded JSON content."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return [
            McpResponse.text("Mixed content"),
            McpResponse.image(PNG, "image/png"),
            McpResponse.resource(
                "test://mixed-content-resource", '{"test":true}', "application/json",
            ),
        ]


class ErrorTool(Tool):
    name = "test_error_handling"
    description = "Return a deliberate tool-domain error."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.error("Intentional conformance error")


class ProgressTool(Tool):
    name = "test_tool_with_progress"
    description = "Report bounded request-scoped progress."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        for current in (0, 50, 100):
            yield McpResponse.progress(current, 100)
            await asyncio.sleep(0.05)
        yield McpResponse.text("Completed progress.")


class ElicitationTool(Tool):
    name = "test_input_required_result_elicitation"
    description = "Request a name through the stateless input-result exchange."

    async def handle(self, request: McpRequest):
        """Produce the declared diagnostic behavior for this fixture."""
        name = accepted(request, "user_name", "name")
        if isinstance(name, str):
            return McpResponse.text(f"Hello {name}")
        return InputRequiredResult(inputRequests={"user_name": elicit()})


class SamplingTool(Tool):
    name = "test_input_required_result_sampling"
    description = "Request client sampling."

    async def handle(self, request: McpRequest):
        """Produce the declared diagnostic behavior for this fixture."""
        response = request.input_responses.get("capital_question")
        if isinstance(response, Mapping):
            return McpResponse.text(str(response.get("content")))
        return InputRequiredResult(inputRequests={"capital_question": sample()})


class RootsTool(Tool):
    name = "test_input_required_result_list_roots"
    description = "Request client roots."

    async def handle(self, request: McpRequest):
        """Produce the declared diagnostic behavior for this fixture."""
        response = request.input_responses.get("client_roots")
        if isinstance(response, Mapping):
            return McpResponse.text(str(response.get("roots")))
        return InputRequiredResult(
            inputRequests={"client_roots": {"method": "roots/list", "params": {}}},
        )


class StateTool(Tool):
    name = "test_input_required_result_request_state"
    description = "Authenticate and decrypt echoed continuation state."

    async def handle(self, request: McpRequest, state: McpState):
        """Produce the declared diagnostic behavior for this fixture."""
        if request.request_state is not msgspec.UNSET:
            state.open(request)
            return McpResponse.text("state-ok")
        return InputRequiredResult(
            inputRequests={"confirm": elicit("ok", "boolean")},
            requestState=state.seal(request, {"stage": 1}),
        )


class TamperedStateTool(StateTool):
    name = "test_input_required_result_tampered_state"


class MultipleInputTool(Tool):
    name = "test_input_required_result_multiple_inputs"
    description = "Request three independent client inputs."

    async def handle(self, request: McpRequest, state: McpState):
        """Produce the declared diagnostic behavior for this fixture."""
        if {"user_name", "greeting", "client_roots"} <= request.input_responses.keys():
            state.open(request)
            return McpResponse.text(str(request.input_responses))
        return InputRequiredResult(
            inputRequests={
                "user_name": elicit(),
                "greeting": sample(),
                "client_roots": {"method": "roots/list", "params": {}},
            },
            requestState=state.seal(request, {"stage": 1}),
        )


class MultiRoundTool(Tool):
    name = "test_input_required_result_multi_round"
    description = "Carry two rounds entirely in authenticated client-echoed state."

    async def handle(self, request: McpRequest, state: McpState):
        """Produce the declared diagnostic behavior for this fixture."""
        previous = (
            state.open(request) if request.request_state is not msgspec.UNSET else {}
        )
        if previous.get("stage") == 2 and accepted(request, "step2", "color"):
            return McpResponse.text(
                f"{previous['name']} likes {accepted(request, 'step2', 'color')}",
            )
        name = accepted(request, "step1", "name")
        if previous.get("stage") == 1 and isinstance(name, str):
            return InputRequiredResult(
                inputRequests={"step2": elicit("color")},
                requestState=state.seal(request, {"stage": 2, "name": name}),
            )
        return InputRequiredResult(
            inputRequests={"step1": elicit()},
            requestState=state.seal(request, {"stage": 1}),
        )


class CapabilitiesTool(Tool):
    name = "test_input_required_result_capabilities"
    description = "Request only capabilities declared on the current call."

    async def handle(self, request: McpRequest):
        """Produce the declared diagnostic behavior for this fixture."""
        inputs = {}
        if "sampling" in request.client_capabilities:
            inputs["greeting"] = sample()
        if "elicitation" in request.client_capabilities:
            inputs["user_name"] = elicit()
        return (
            InputRequiredResult(inputRequests=inputs)
            if inputs
            else McpResponse.text("No client inputs supported")
        )


class MissingCapabilityTool(SamplingTool):
    name = "test_missing_capability"


class StreamingElicitationTool(Tool):
    name = "test_streaming_elicitation"
    description = "Yield an input-required result within a response stream."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        yield InputRequiredResult(inputRequests={"user_name": elicit()})


class LoggingTool(SimpleText):
    name = "test_logging_tool"


class TriggerTools(Tool):
    name = "test_trigger_tool_change"
    description = "Publish an authorized tool-list change event."

    async def handle(self, manager: IMcpManager):
        """Produce the declared diagnostic behavior for this fixture."""
        await manager.toolsChanged(ConformanceServer)
        return McpResponse.text("Tool-list notification published")


class TriggerPrompts(Tool):
    name = "test_trigger_prompt_change"
    description = "Publish an authorized prompt-list change event."

    async def handle(self, manager: IMcpManager):
        """Produce the declared diagnostic behavior for this fixture."""
        await manager.promptsChanged(ConformanceServer)
        return McpResponse.text("Prompt-list notification published")


class StaticText(Resource):
    name = "static_text"
    uri = "test://static-text"
    description = "A diagnostic plain-text resource."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.resource(self.uri, "Static test resource", "text/plain")


class StaticBinary(Resource):
    name = "static_binary"
    uri = "test://static-binary"
    mime_type = "image/png"
    description = "A diagnostic binary PNG resource."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.resource(self.uri, PNG, self.mime_type)


class TemplateResource(Resource):
    name = "template_resource"
    uri_template = "test://template/{id}/data"
    mime_type = "application/json"
    description = "A deterministic URI template fixture."

    async def handle(self, id: str):  # noqa: A002 - Official URI variable name.
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.resource(
            f"test://template/{id}/data",
            json.dumps(
                {
                    "id": id,
                    "templateTest": True,
                    "data": f"Data for ID: {id}",
                },
            ),
            self.mime_type,
        )


class SimplePrompt(Prompt):
    name = "test_simple_prompt"
    description = "A plain text prompt."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.text("Provide a helpful answer.")


class ArgumentsPrompt(Prompt):
    name = "test_prompt_with_arguments"
    description = "A prompt with two required arguments and completions."
    arguments = (
        PromptArgument(name="arg1", required=True),
        PromptArgument(name="arg2", required=True),
    )

    async def handle(self, arg1: str, arg2: str):
        """Produce the declared diagnostic behavior for this fixture."""
        return McpResponse.text(f"Arguments: {arg1}, {arg2}")

    async def complete(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return Completion(values=("paris", "park", "party"))


class EmbeddedPrompt(Prompt):
    name = "test_prompt_with_embedded_resource"
    description = "A prompt with an embedded resource."
    arguments = (PromptArgument(name="resourceUri", required=True),)

    async def handle(self, resourceUri: str):  # noqa: N803 - Official prompt argument name.
        """Produce the declared diagnostic behavior for this fixture."""
        return [
            McpResponse.text("Use this resource"),
            McpResponse.resource(resourceUri, "Prompt resource", "text/plain"),
        ]


class ImagePrompt(Prompt):
    name = "test_prompt_with_image"
    description = "A prompt containing an image."

    async def handle(self):
        """Produce the declared diagnostic behavior for this fixture."""
        return [
            McpResponse.text("Describe this image"),
            McpResponse.image(PNG, "image/png"),
        ]


class InputPrompt(Prompt):
    name = "test_input_required_result_prompt"
    description = "Request prompt context from the client."

    async def handle(self, request: McpRequest):
        """Produce the declared diagnostic behavior for this fixture."""
        context = accepted(request, "user_context", "context")
        if isinstance(context, str):
            return McpResponse.text(f"Use context: {context}")
        return InputRequiredResult(inputRequests={"user_context": elicit("context")})


class ConformanceServer(Server):
    name = "Orionis conformance fixture"
    version = "1.0.0"
    instructions = "Diagnostic fixtures for the official 2026-07-28 conformance suite."
    list_changed = True
    resource_subscriptions = True
    tools = (
        SimpleText,
        ImageTool,
        AudioTool,
        EmbeddedTool,
        MixedTool,
        ErrorTool,
        ProgressTool,
        ElicitationTool,
        SamplingTool,
        RootsTool,
        StateTool,
        TamperedStateTool,
        MultipleInputTool,
        MultiRoundTool,
        CapabilitiesTool,
        MissingCapabilityTool,
        StreamingElicitationTool,
        LoggingTool,
        TriggerTools,
        TriggerPrompts,
    )
    resources = (StaticText, StaticBinary, TemplateResource)
    prompts = (SimplePrompt, ArgumentsPrompt, EmbeddedPrompt, ImagePrompt, InputPrompt)
