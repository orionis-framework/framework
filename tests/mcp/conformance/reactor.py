"""Run the ordinary native Reactor command with isolated fixture registrations."""

import sys

from orionis.console.stdio import protocol_stdio
from orionis.aio import Loop

if __name__ == "__main__":
    with protocol_stdio(["mcp:start", "conformance"]):
        from tests.mcp.conformance.app import app

        sys.exit(Loop.run(app.handleCommand(["mcp:start", "conformance"])))
