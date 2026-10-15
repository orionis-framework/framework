"""Aggregate independent load runs and publish machine-readable artifacts."""

import csv
import json
import statistics
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

METRICS = (
    "requests_per_second",
    "mean_latency_ms",
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
)
FIELDS = (
    "framework",
    "interface",
    "workers",
    "status",
    *METRICS,
    "requests",
    "errors",
    "reason",
)


def aggregate_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate independent runs without publishing metrics for failed samples.

    Parameters
    ----------
    samples : list[dict[str, Any]]
        Normalized measured runs, excluding warmup.

    Returns
    -------
    dict[str, Any]
        Samples, totals, status, and either per-run medians or a failure reason.

    Raises
    ------
    ValueError
        If no measured runs are supplied.
    """
    # Require actual measurements before constructing a comparative result.
    if not samples:
        error_msg = "At least one measured run is required"
        raise ValueError(error_msg)
    result = {
        "samples": samples,
        "requests": sum(sample["requests"] for sample in samples),
        "errors": sum(sample["errors"] for sample in samples),
    }
    # Withhold all comparative metrics when even one measured run has errors.
    if result["errors"]:
        result.update(
            status="failed", reason="HTTP or transport errors during measurement",
        )
    else:
        result.update(status="ok")
        result.update(
            {
                metric: statistics.median(sample[metric] for sample in samples)
                for metric in METRICS
            },
        )
    return result


def write_json(path: Path, value: object) -> None:
    """
    Write strict UTF-8 JSON with a trailing newline.

    Parameters
    ----------
    path : Path
        Destination file in an existing directory.
    value : object
        JSON-serializable payload.

    Returns
    -------
    None
        Persist the payload at the supplied path.
    """
    # Reject NaN and infinity so artifacts remain portable across JSON readers.
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def render_summary(report: dict[str, Any]) -> str:
    """
    Render comparative metrics, environment details, and failures as Markdown.

    Parameters
    ----------
    report : dict[str, Any]
        Settings, environment metadata, and configuration results.

    Returns
    -------
    str
        Markdown summary with a trailing newline and explicit failure details.
    """
    # State the measurement policy before presenting comparable rows.
    settings = report["settings"]
    lines = [
        "# HTTP framework comparison",
        "",
        (
            f"{settings['connections']} connections; "
            f"{settings['warmup_seconds']}s warmup; "
            f"{settings['repetitions']} x "
            f"{settings['duration_seconds']}s per configuration."
        ),
        (
            "HTTP/1.1 keep-alive; Granian runtime threads: 1; "
            "asyncio; oha worker threads: 1."
        ),
        (
            "Medians of individual runs; throughput counts HTTP 200 only. "
            "Latency is in ms."
        ),
        "",
        (
            "| Framework | Interface | Workers | Status | Requests/s | "
            "Mean | p50 | p95 | p99 | Errors |"
        ),
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    # Use placeholders rather than invented values for unavailable metrics.
    for row in report["results"]:
        values = [f"{row[metric]:.2f}" if metric in row else "-" for metric in METRICS]
        lines.append(
            f"| {row['framework']} | {row['interface']} | {row['workers']} | "
            f"{row['status']} | {' | '.join(values)} | {row.get('errors', '-')} |",
        )
    # Keep the runtime context alongside the numbers it qualifies.
    lines.extend(["", "## Environment", ""])
    environment = report["environment"]
    lines.extend(
        f"- {key}: {environment.get(key, '')}"
        for key in ("os", "cpu", "logical_cpus", "python", "commit", "dirty", "run_url")
    )
    for package, package_version in environment["versions"].items():
        lines.append(f"- {package}: {package_version}")
    lines.extend(
        [
            "",
            (
                "GitHub-hosted runners vary; this Hello World test "
                "does not represent a full application."
            ),
        ],
    )
    # Retain setup and per-case failure reasons beside any successful results.
    failures = [row for row in report["results"] if row.get("reason")]
    if failures or report.get("error"):
        lines.extend(["", "## Incomplete or failed measurements", ""])
        if report.get("error"):
            lines.append(f"- Setup: {report['error']}")
        lines.extend(
            f"- {row['framework']} ({row['interface']}) / "
            f"{row['workers']} workers: {row['reason']}"
            for row in failures
        )
    return "\n".join(lines) + "\n"


def write_reports(output: Path, report: dict[str, Any]) -> str:
    """
    Persist consistent JSON, CSV, environment, and Markdown artifacts.

    Parameters
    ----------
    output : Path
        Existing directory in which to write report files.
    report : dict[str, Any]
        Complete or partial comparison report to serialize.

    Returns
    -------
    str
        Markdown summary also saved as ``summary.md``.
    """
    # Derive every artifact from the same report to prevent divergent summaries.
    write_json(output / "summary.json", report)
    write_json(output / "environment.json", report["environment"])
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["results"])
    markdown = render_summary(report)
    (output / "summary.md").write_text(markdown, encoding="utf-8")
    return markdown
