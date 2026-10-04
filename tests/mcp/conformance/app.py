"""Native no-cache ASGI application for external interoperability probes."""

import os
from pathlib import Path
import tempfile

from orionis.foundation.application import Application

port = int(os.environ.get("ORIONIS_MCP_TEST_PORT", "8765"))
app = Application(base_path=Path(__file__).resolve().parents[3])
app.withConfigPaths(
    config="tests/mcp/conformance/config",
    storage_framework=Path(tempfile.gettempdir())
    / "orionis-mcp-reference"
    / "fixture-storage",
)
app.withRouting(ai="tests/mcp/conformance/routes.py")
app.withConfigApp(
    name="MCP conformance",
    debug=False,
    cipher="AES-256-GCM",
    key=b"0123456789abcdef0123456789abcdef",
)
app.withConfigMcp(
    allowed_origins=(
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"http://[::1]:{port}",
    ),
)
app.create()
