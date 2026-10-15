import argparse
import json
import os
from pathlib import Path
from typing import Any

# ruff: noqa: T201

def render_report(reports: list[dict[str, Any]]) -> str: # NOSONAR
    """
    Render benchmark measurements, load settings, and runner metadata.

    Parameters
    ----------
    reports : list[dict[str, Any]]
        Platform reports containing results, settings, and environment details.

    Returns
    -------
    str
        Markdown report ending with a newline, including failure explanations.
    """
    # State measurement limits before presenting cross-platform runner results.
    lines = [
        "# Orionis HTTP Hello World benchmark",
        "",
        (
            "Real Orionis public API route, `GET /` -> `200 Hello World`, "
            "Granian RSGI, HTTP/1.1 keep-alive, asyncio, "
            "one runtime thread per worker."
        ),
        "",
        (
            "REQ/SEG is the median successful HTTP 200 requests/second "
            "across measured runs. "
            "Latency columns are medians of each run's mean and p95. "
            "Requests and errors are totals across measured runs; warmup is excluded."
        ),
        "",
        (
            "Client and server share the CI runner. "
            "Hardware and runner contention vary; "
            "these results are diagnostic and do not establish production capacity "
            "or a controlled comparison between operating systems."
        ),
        "",
        (
            "| Platform | Workers | Status | REQ/SEG | Requests | Errors | "
            "Mean (ms) | p95 (ms) |"
        ),
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    # Leave unmeasured configurations blank instead of inventing numeric results.
    for report in reports:
        for row in report["results"]:
            measured = "requests_per_second" in row
            cells = [
                report["platform"],
                str(row["workers"]),
                row["status"],
                f"{row['requests_per_second']:,.2f}" if measured else "-",
                f"{row['requests']:,}" if measured else "-",
                str(row["errors"]) if measured else "-",
                f"{row['mean_latency_ms']:.3f}" if measured else "-",
                f"{row['p95_latency_ms']:.3f}" if measured else "-",
            ]
            lines.append("| " + " | ".join(cells) + " |")
    # Retain reproducibility metadata and failure reasons below the summary table.
    for report in reports:
        lines.extend(["", f"## {report['platform']}", ""])
        settings = report["settings"]
        lines.append(
            f"{settings['connections']} connections; "
            f"{settings['warmup_seconds']}s warmup; "
            f"{settings['repetitions']} x {settings['duration_seconds']}s "
            "measured per worker count.",
        )
        lines.append("")
        for key, value in report["environment"].items():
            if value != "":
                lines.append(f"- {key}: {value}")
        if report.get("error"):
            # Keep setup failures visible even when no worker was measured.
            lines.extend(["", f"Setup failed: {report['error']}"])
        for row in report["results"]:
            if row.get("reason"):
                lines.extend(
                    [
                        "",
                        f"Workers {row['workers']} ({row['status']}): {row['reason']}",
                    ],
                )
    return "\n".join(lines) + "\n"

def write_report(output: Path, report: dict[str, Any], markdown: str) -> None:
    """
    Save report artifacts and append Markdown to the Actions summary.

    Parameters
    ----------
    output : Path
        Directory to create for the JSON and Markdown artifacts.
    report : dict[str, Any]
        JSON-serializable platform report or combined report payload.
    markdown : str
        Rendered report to save, print, and append to the job summary.

    Returns
    -------
    None
        Write both artifacts and publish Markdown to configured output streams.
    """
    # Persist machine-readable and rendered versions of the same report.
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "report.md").write_text(markdown, encoding="utf-8")
    print(markdown, flush=True)
    # Append rather than overwrite other steps' existing Actions summary content.
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(markdown)

def main() -> int:
    """
    Aggregate platform artifacts and flag missing or failed measurements.

    Returns
    -------
    int
        Zero for a complete, successful platform matrix, otherwise one.
    """
    # Resolve input artifacts separately from the combined report destination.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    reports = []
    errors = []
    # Preserve valid artifacts while collecting errors from unreadable reports.
    for path in sorted(args.input_dir.rglob("report.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            if report["schema_version"] != 1:
                error_msg = "Unsupported report schema"
                raise ValueError(error_msg)
            # Validate required report fields before rendering combined output.
            render_report([report])
            workers = [row["workers"] for row in report["results"]]
            missing_workers = {1, 2, 3, 4} - set(workers)
            # Require exactly one result for each configured worker count.
            if missing_workers:
                errors.append(
                    f"{report['platform']}: missing worker results: "
                    + ", ".join(str(worker) for worker in sorted(missing_workers)),
                )
            if len(workers) != len(set(workers)):
                errors.append(f"{report['platform']}: duplicate worker results")
            reports.append(report)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            # Include artifact failures in the final report instead of dropping them.
            errors.append(f"Cannot read {path}: {error}")
    # Distinguish missing platform jobs from failures within available artifacts.
    present = {report["platform"] for report in reports}
    missing = {"Linux", "Windows", "macOS"} - present
    if missing:
        errors.append("Missing platform reports: " + ", ".join(sorted(missing)))
    markdown = render_report(reports)
    if errors:
        # Publish partial measurements alongside a visible completeness warning.
        markdown += (
            "\n## Incomplete report\n\n"
            + "\n".join(f"- {error}" for error in errors)
            + "\n"
        )
    write_report(
        args.output_dir,
        {"schema_version": 1, "platforms": reports, "errors": errors},
        markdown,
    )
    # Preserve failures reported by individual workers or platform setup.
    failed = any(
        report.get("error")
        or any(row["status"] == "failed" for row in report["results"])
        for report in reports
    )
    return int(bool(errors) or failed)

# Propagate completeness and measurement failures to the calling CI job.
if __name__ == "__main__":
    raise SystemExit(main())
