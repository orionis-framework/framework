"""Provide console commands bootstrap operations.

Includes ``BootstrapApiCommand``, ``BootstrapAiCommand``,
``BootstrapConsoleCommand``, ``BootstrapWebCommand``.
"""

from orionis.console.commands.bootstrap._base import BootstrapCommand


class BootstrapApiCommand(BootstrapCommand):
    """Enable API routes and their HTTP component directories."""

    # Bind the native Reactor signature to the API routing context.
    signature = "bootstrap:api"
    """Bind the native Reactor signature to the API routing context."""
    description = "Create and register API routing and HTTP component paths."
    """
    Description identifier: ``Create and register API routing and HTTP component
    paths.``.
    """
    context = "api"
    """Context identifier: ``api``."""


class BootstrapAiCommand(BootstrapCommand):
    """Enable AI routes and their MCP component directories."""

    # Bind the native Reactor signature to the AI routing context.
    signature = "bootstrap:ai"
    """Bind the native Reactor signature to the AI routing context."""
    description = "Create and register AI routing and MCP component paths."
    """
    Description identifier: ``Create and register AI routing and MCP component
    paths.``.
    """
    context = "ai"
    """Context identifier: ``ai``."""


class BootstrapConsoleCommand(BootstrapCommand):
    """Enable console routes and their command component directories."""

    # Bind the native Reactor signature to the console routing context.
    signature = "bootstrap:console"
    """Bind the native Reactor signature to the console routing context."""
    description = "Create and register console routing and command paths."
    """
    Description identifier: ``Create and register console routing and command
    paths.``.
    """
    context = "console"
    """Context identifier: ``console``."""


class BootstrapWebCommand(BootstrapCommand):
    """Enable web routes and their HTTP component directories."""

    # Bind the native Reactor signature to the web routing context.
    signature = "bootstrap:web"
    """Bind the native Reactor signature to the web routing context."""
    description = "Create and register web routing and HTTP component paths."
    """
    Description identifier: ``Create and register web routing and HTTP component
    paths.``.
    """
    context = "web"
    """Context identifier: ``web``."""


class BootstrapWebsocketCommand(BootstrapCommand):
    """Enable WebSocket routes and their HTTP component directories."""

    # Bind the native Reactor signature to the WebSocket routing context.
    signature = "bootstrap:websocket"
    """Bind the native Reactor signature to the WebSocket routing context."""
    description = "Create and register WebSocket routing and HTTP component paths."
    """
    Description identifier: ``Create and register WebSocket routing and HTTP
    component paths.``.
    """
    context = "websocket"
    """Context identifier: ``websocket``."""
