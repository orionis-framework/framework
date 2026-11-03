"""Describe registered servers without opening their transports."""

from orionis.console.base.command import BaseCommand
from orionis.mcp.contracts.manager import IMcpManager

# ruff: noqa: TC001

class McpListCommand(BaseCommand):
    """Describe registered servers without opening their transports."""

    timestamps = False
    """Timestamps flag used by ``McpListCommand``."""
    signature = "mcp:list"
    """Signature identifier: ``mcp:list``."""
    description = "List registered HTTP and local MCP servers."
    """Description identifier: ``List registered HTTP and local MCP servers.``."""

    async def handle(self, manager: IMcpManager) -> None:
        """
        Show each transport, address and server declaration.

        Parameters
        ----------
        manager : orionis.mcp.contracts.manager.IMcpManager
            Value supplied for ``manager``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        rows = [
            (transport, address, f"{server.__module__}.{server.__qualname__}")
            for transport, address, server in manager.servers()
        ]
        if not rows:
            self.info("No MCP servers are registered.")
            return
        self.table(["Transport", "Endpoint / handle", "Server"], rows)
