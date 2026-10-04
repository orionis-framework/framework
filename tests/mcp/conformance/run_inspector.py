"""Run pinned modern Inspector smoke probes over native HTTP and STDIO."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

INSPECTOR_VERSION = "2.9.0"
PROBES = (
    ("tools-list", ("--method", "tools/list")),
    ("tools-call", ("--method", "tools/call", "--tool-name", "test_simple_text")),
    (
        "tools-progress",
        ("--method", "tools/call", "--tool-name", "test_tool_with_progress"),
    ),
    ("resources-list", ("--method", "resources/list")),
    ("resources-text", ("--method", "resources/read", "--uri", "test://static-text")),
    (
        "resources-binary",
        ("--method", "resources/read", "--uri", "test://static-binary"),
    ),
    ("prompts-list", ("--method", "prompts/list")),
    ("prompts-get", ("--method", "prompts/get", "--prompt-name", "test_simple_prompt")),
)


def main() -> int:
    """Record each external CLI result and fail on any failed probe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", required=True, type=Path)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    arguments = parser.parse_args()
    package = arguments.tools.resolve() / "node_modules/@modelcontextprotocol/inspector"
    installed = json.loads((package / "package.json").read_text(encoding="utf-8"))
    if installed.get("version") != INSPECTOR_VERSION:
        parser.error(f"Expected Inspector {INSPECTOR_VERSION}.")
    node = shutil.which("node")
    if node is None:
        parser.error("Node.js must be on PATH.")
    output = arguments.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[3]
    config = output / "stdio-config.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "orionis": {
                        "type": "stdio",
                        "command": sys.executable,
                        "args": ["-B", "-m", "tests.mcp.conformance.reactor"],
                        "protocolEra": "modern",
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    executable = [node, str(package / "clients/launcher/build/index.js"), "--cli"]
    transports = {
        "http": (
            "--server-url",
            arguments.url,
            "--transport",
            "http",
            "--protocol-era",
            "modern",
            "--stored-auth-only",
        ),
        "stdio": ("--config", str(config), "--server", "orionis", "--cwd", str(repo)),
    }
    checks = []
    for transport, options in transports.items():
        for name, probe in PROBES:
            command = [*executable, *options, *probe, "--format", "json"]
            result = subprocess.run(  # noqa: S603 - Explicit external oracle argv.
                command,
                cwd=repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            (output / f"{transport}-{name}.stdout.json").write_text(
                result.stdout, encoding="utf-8",
            )
            (output / f"{transport}-{name}.stderr.log").write_text(
                result.stderr, encoding="utf-8",
            )
            checks.append(
                {"transport": transport, "probe": name, "exit": result.returncode},
            )
    (output / "summary.json").write_text(
        json.dumps(
            {
                "inspector": INSPECTOR_VERSION,
                "protocolVersion": "2026-07-28",
                "checks": checks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    passed = sum(item["exit"] == 0 for item in checks)
    sys.stdout.write(f"Inspector: {passed}/{len(checks)} passed\n")
    return int(any(item["exit"] for item in checks))


if __name__ == "__main__":
    raise SystemExit(main())
