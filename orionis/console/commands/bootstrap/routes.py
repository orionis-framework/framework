from orionis.console.commands.bootstrap._base import BootstrapCommand

class BootstrapApiCommand(BootstrapCommand):
    """Enable API routes and their HTTP component directories."""

    # Bind the native Reactor signature to the API routing context.
    signature = "bootstrap:api"
    description = "Create and register API routing and HTTP component paths."
    context = "api"

class BootstrapAiCommand(BootstrapCommand):
    """Enable AI routes and their MCP component directories."""

    # Bind the native Reactor signature to the AI routing context.
    signature = "bootstrap:ai"
    description = "Create and register AI routing and MCP component paths."
    context = "ai"

class BootstrapConsoleCommand(BootstrapCommand):
    """Enable console routes and their command component directories."""

    # Bind the native Reactor signature to the console routing context.
    signature = "bootstrap:console"
    description = "Create and register console routing and command paths."
    context = "console"

class BootstrapWebCommand(BootstrapCommand):
    """Enable web routes and their HTTP component directories."""

    # Bind the native Reactor signature to the web routing context.
    signature = "bootstrap:web"
    description = "Create and register web routing and HTTP component paths."
    context = "web"

class BootstrapWebsocketCommand(BootstrapCommand):
    """Enable WebSocket routes and their HTTP component directories."""

    # Bind the native Reactor signature to the WebSocket routing context.
    signature = "bootstrap:websocket"
    description = "Create and register WebSocket routing and HTTP component paths."
    context = "websocket"
