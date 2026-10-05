import sys
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.mcp.contracts.manager import IMcpManager

# ruff: noqa: TC001

class McpStartCommand(BaseCommand):
    """Run one explicitly registered local MCP server."""

    timestamps = False
    signature = "mcp:start"
    description = "Start a registered MCP 2026-07-28 server over STDIO."
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name", type_=str, required=True,
            help="Local server handle.",
        ),
    ]

    async def handle(self, manager: IMcpManager) -> int:
        """
        Preserve protocol-only STDOUT and fail unknown handles without imports.

        Parameters
        ----------
        manager : IMcpManager
            Value supplied for ``manager``.

        Returns
        -------
        int
            Result of the operation described above.
        """
        name = self.getArgument("name")
        if not isinstance(name, str):
            sys.stderr.write("An MCP local server handle is required.\n")
            return 1
        try:
            manager.getLocalServer(name)
        except KeyError:
            sys.stderr.write(f"MCP local server {name!r} is not registered.\n")
            return 1
        await manager.startLocal(name)
        return 0
