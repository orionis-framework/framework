"""Preserve external oracle outcomes without storing machine-specific paths."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def load_run(directory: Path, required: set[str], log: Path, interface: str) -> dict:
    """Preserve one complete frozen requirement run for a native interface."""
    scenarios = []
    for folder in sorted(directory.iterdir()):
        if not folder.is_dir() or not (folder / "checks.json").is_file():
            continue
        name = re.split(r"-\d{4}-\d{2}-\d{2}T", folder.name.removeprefix("server-"))[0]
        raw = json.loads((folder / "checks.json").read_text(encoding="utf-8"))
        scenarios.append(
            {
                "name": name,
                "required": name in required,
                "counts": dict(Counter(check["status"] for check in raw)),
                "checks": [
                    {
                        key: check[key]
                        for key in (
                            "id",
                            "status",
                            "timestamp",
                            "errorMessage",
                        )
                        if key in check
                    }
                    for check in raw
                ],
            },
        )
    covered = [scenario["name"] for scenario in scenarios if scenario["required"]]
    if len(covered) != len(required) or set(covered) != required:
        message = "Each required scenario must have exactly one saved run."
        raise ValueError(message)
    counts = Counter(
        check["status"]
        for scenario in scenarios
        if scenario["required"]
        for check in scenario["checks"]
    )
    return {
        "interface": interface,
        "requiredScenarios": len(covered),
        "requiredCheckCounts": dict(counts),
        "conformanceLogSha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "scenarios": scenarios,
    }


def main() -> int:
    """Aggregate exact official check statuses and Inspector process outcomes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conformance", required=True, type=Path)
    parser.add_argument("--inspector", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rsgi", type=Path)
    parser.add_argument("--rsgi-log", type=Path)
    args = parser.parse_args()
    manifest = json.loads(
        (Path(__file__).parent / "fixture-requirements.json").read_text(
            encoding="utf-8",
        ),
    )
    required = {entry["name"] for entry in manifest["scenarios"]}
    run = load_run(args.conformance, required, args.log, "asgi")
    inspector = json.loads(
        (args.inspector / "summary.json").read_text(encoding="utf-8"),
    )
    report = {
        "officialSchema": json.loads(
            (
                Path(__file__).parent.parent / "fixtures/official_schema.source.json"
            ).read_text(encoding="utf-8"),
        ),
        "protocolVersion": manifest["protocolVersion"],
        "conformancePackage": manifest["conformancePackage"],
        "conformanceSourceCommit": manifest["sourceCommit"],
        **run,
        "knownFailureBaseline": None,
        "fixture": "tests.mcp.conformance.app:app (native ASGI/Granian)",
        "stdioFixture": "python -B -m tests.mcp.conformance.reactor",
        "inspector": inspector,
    }
    if args.rsgi is not None:
        if args.rsgi_log is None:
            parser.error("--rsgi also requires --rsgi-log.")
        report["rsgi"] = load_run(args.rsgi, required, args.rsgi_log, "rsgi")
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return int(
        bool(run["requiredCheckCounts"].get("FAILURE"))
        or bool(report.get("rsgi", {}).get("requiredCheckCounts", {}).get("FAILURE"))
        or any(check["exit"] for check in inspector["checks"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
