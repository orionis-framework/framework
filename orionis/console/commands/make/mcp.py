"""Provide console commands make operations.

Includes ``MakeMcpServer``, ``MakeMcpTool``, ``MakeMcpResource``, ``MakeMcpPrompt``.
"""

from orionis.console.commands.make._base import MakeStubCommand

class MakeMcpServer(MakeStubCommand):
    """Generate a transport-independent MCP server declaration."""

    timestamps = False
    """Timestamps flag used by ``MakeMcpServer``."""
    signature = "make:mcp-server"
    """Signature identifier: ``make:mcp-server``."""
    description = "Create a new MCP server."
    """Description identifier: ``Create a new MCP server.``."""
    template_name = "mcp_server"
    """Template name identifier: ``mcp_server``."""
    path_key = "app_mcp_servers"
    """Path key identifier: ``app_mcp_servers``."""
    success_label = "MCP server"
    """Success label identifier: ``MCP server``."""
    postfix = "Server"
    """Postfix identifier: ``Server``."""

class MakeMcpTool(MakeStubCommand):
    """Generate a typed MCP tool with a native Orionis input schema."""

    timestamps = False
    """Timestamps flag used by ``MakeMcpTool``."""
    signature = "make:mcp-tool"
    """Signature identifier: ``make:mcp-tool``."""
    description = "Create a new MCP tool."
    """Description identifier: ``Create a new MCP tool.``."""
    template_name = "mcp_tool"
    """Template name identifier: ``mcp_tool``."""
    path_key = "app_mcp_tools"
    """Path key identifier: ``app_mcp_tools``."""
    success_label = "MCP tool"
    """Success label identifier: ``MCP tool``."""
    postfix = "Tool"
    """Postfix identifier: ``Tool``."""

class MakeMcpResource(MakeStubCommand):
    """Generate an explicitly addressed MCP resource."""

    timestamps = False
    """Timestamps flag used by ``MakeMcpResource``."""
    signature = "make:mcp-resource"
    """Signature identifier: ``make:mcp-resource``."""
    description = "Create a new MCP resource."
    """Description identifier: ``Create a new MCP resource.``."""
    template_name = "mcp_resource"
    """Template name identifier: ``mcp_resource``."""
    path_key = "app_mcp_resources"
    """Path key identifier: ``app_mcp_resources``."""
    success_label = "MCP resource"
    """Success label identifier: ``MCP resource``."""
    postfix = "Resource"
    """Postfix identifier: ``Resource``."""

class MakeMcpPrompt(MakeStubCommand):
    """Generate an MCP prompt declaration and asynchronous handler."""

    timestamps = False
    """Timestamps flag used by ``MakeMcpPrompt``."""
    signature = "make:mcp-prompt"
    """Signature identifier: ``make:mcp-prompt``."""
    description = "Create a new MCP prompt."
    """Description identifier: ``Create a new MCP prompt.``."""
    template_name = "mcp_prompt"
    """Template name identifier: ``mcp_prompt``."""
    path_key = "app_mcp_prompts"
    """Path key identifier: ``app_mcp_prompts``."""
    success_label = "MCP prompt"
    """Success label identifier: ``MCP prompt``."""
    postfix = "Prompt"
    """Postfix identifier: ``Prompt``."""
