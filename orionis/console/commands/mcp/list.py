from orionis.console.base.command import BaseCommand
from orionis.mcp.contracts.manager import IMcpManager  # noqa: TC001 - Command DI.


class McpListCommand(BaseCommand):
    """Describe registered servers without opening their transports."""

    timestamps = False
    signature = "mcp:list"
    description = "List registered HTTP and local MCP servers."

    async def handle(self, manager: IMcpManager) -> None:  # pyright: ignore[reportIncompatibleMethodOverride] - Native command DI.
        """Show each transport, address and server declaration."""
        rows = [
            (transport, address, f"{server.__module__}.{server.__qualname__}")
            for transport, address, server in manager.servers()
        ]
        if not rows:
            self.info("No MCP servers are registered.")
            return
        self.table(["Transport", "Endpoint / handle", "Server"], rows)
