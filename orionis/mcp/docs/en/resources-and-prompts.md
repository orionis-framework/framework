# Resources, URI templates and prompts

Resources publish URI-addressed content; prompts produce conversation messages. Neither implicitly grants filesystem access nor executes a language model. Handlers use application services for data and retain the same access checks as tools.

## Publishing a parameterized resource

```python
from orionis.mcp import McpResponse, Resource, Server
from orionis.mcp.server.compiler import compile_server

class UserResource(Resource):
    uri_template = "demo://users/{user_id}"
    mime_type = "application/json"

    def handle(self, user_id: str) -> McpResponse:
        return McpResponse.structured({"id": user_id})

class DirectoryServer(Server):
    name = "Directory"
    resources = (UserResource,)

assert len(compile_server(DirectoryServer).templates) == 1
```

Declare exactly one absolute `uri` or `uri_template`. Handlers can receive decoded variables by name or an injected `McpRequest` with `uri`, `uri_variables` and parameters. Authorize the identity against the requested record; knowing an identifier does not grant read access.

Templates follow RFC 6570 level four through `uritemplate`. Simple forms support automatic inversion; complex forms require a synchronous static/class `match(uri)` method returning variables or `None`. Matching checks that re-expansion produces the original URI. Do not accept partial matches. Prefixes on lists/mappings are rejected; integration preserves boolean formatting, mapping order and UTF-8 escaping.

`name`, `title`, `description`, `icons`, `meta`, `cache`, `size` and `annotations` describe the catalog. A URI is not a disk-read command; implement safe access in the handler and avoid exposing sensitive internal paths.

## Building a reusable prompt

```python
from orionis.mcp import Completion, McpResponse, Prompt, PromptArgument, Server
from orionis.mcp.server.compiler import compile_server

class ExplainPrompt(Prompt):
    arguments = (PromptArgument(name="topic", required=True),)

    def handle(self, topic: str) -> McpResponse:
        return McpResponse.text(f"Explain {topic}").asUser()

    def complete(self) -> Completion:
        return Completion(values=("sessions", "routing"))

class GuideServer(Server):
    name = "Guide"
    prompts = (ExplainPrompt,)

assert "explain" in compile_server(GuideServer).prompts
```

Prompt arguments are strings; do not declare complex JSON as if this were Tool input. `required=True` requires presence. Return multiple `McpResponse` values with `asUser()` or `asAssistant()` to construct messages. Templates containing external content are not inherently trusted instructions; consuming applications must retain provenance.

`complete()` supplies prompt or resource-template suggestions. It may return `Completion` or a string list/tuple, capped at 100 values. Inject context when needing `request.params`; access checks run first. Unknown arguments/references fail as invalid parameters.

## Paginated catalogs

The dispatcher lists resources, templates and prompts with opaque cursors and bounded pages. A cursor belongs to its method; do not construct one or reuse it for another catalog. Visibility/authorization is evaluated per request and pages may change with identity or data. Clients should follow `nextCursor` until exhausted without assuming later access to everything previously listed.

Evidence: [primitives](../../server/primitives.py), [URI matcher](../../server/templates.py), [dispatcher](../../dispatcher.py), [metadata](../../protocol/metadata.py). Tests: [templates](../../../../tests/mcp/server/test_templates.py), [dispatcher](../../../../tests/mcp/test_dispatcher.py), [edge cases](../../../../tests/mcp/test_dispatcher_edges.py). Continue with [serialization](responses-and-content.md).
