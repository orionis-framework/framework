"""Run the pinned official MCP referee against an already running test server."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess


PROTOCOL_VERSION = "2026-07-28"
CONFORMANCE_VERSION = "0.2.0-alpha.12"


def main() -> int:
    """Select the frozen modern requirement set and preserve the referee exit code.

    Returns
    -------
    int
        Official conformance result, or a usage error for missing tools.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", required=True, type=Path)
    parser.add_argument("--list", action="store_true", dest="list_scenarios")
    parser.add_argument("--url")
    parser.add_argument("--output-dir", type=Path)
    arguments = parser.parse_args()
    package = (
        arguments.tools.resolve()
        / "node_modules/@modelcontextprotocol/conformance"
    )
    manifest = package / "package.json"
    if not manifest.is_file():
        parser.error("Install the pinned conformance package under --tools first.")
    installed = json.loads(manifest.read_text(encoding="utf-8"))
    if installed.get("version") != CONFORMANCE_VERSION:
        parser.error(f"Expected conformance {CONFORMANCE_VERSION}.")
    node = shutil.which("node")
    if node is None:
        parser.error("Node.js must be installed and available on PATH.")
    command = [node, str(package / "dist/index.js")]
    if arguments.list_scenarios:
        command += ["list", "--requirements", PROTOCOL_VERSION]
    else:
        if arguments.url is None or arguments.output_dir is None:
            parser.error("A run requires --url and --output-dir.")
        command += [
            "server", "--url", arguments.url,
            "--requirements", PROTOCOL_VERSION,
            "--output-dir", str(arguments.output_dir.resolve()),
        ]
    # The executable is resolved explicitly; arguments never pass through a shell.
    return subprocess.run(command, check=False).returncode  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main())
