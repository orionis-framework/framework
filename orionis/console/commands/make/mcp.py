from orionis.console.commands.make._base import MakeStubCommand

class MakeMcpServer(MakeStubCommand):
    """Generate a transport-independent MCP server declaration."""

    timestamps = False
    signature = "make:mcp-server"
    description = "Create a new MCP server."
    template_name = "mcp_server"
    path_key = "app_mcp_servers"
    success_label = "MCP server"
    postfix = "Server"

class MakeMcpTool(MakeStubCommand):
    """Generate a typed MCP tool with a native Orionis input schema."""

    timestamps = False
    signature = "make:mcp-tool"
    description = "Create a new MCP tool."
    template_name = "mcp_tool"
    path_key = "app_mcp_tools"
    success_label = "MCP tool"
    postfix = "Tool"

class MakeMcpResource(MakeStubCommand):
    """Generate an explicitly addressed MCP resource."""

    timestamps = False
    signature = "make:mcp-resource"
    description = "Create a new MCP resource."
    template_name = "mcp_resource"
    path_key = "app_mcp_resources"
    success_label = "MCP resource"
    postfix = "Resource"

class MakeMcpPrompt(MakeStubCommand):
    """Generate an MCP prompt declaration and asynchronous handler."""

    timestamps = False
    signature = "make:mcp-prompt"
    description = "Create a new MCP prompt."
    template_name = "mcp_prompt"
    path_key = "app_mcp_prompts"
    success_label = "MCP prompt"
    postfix = "Prompt"
