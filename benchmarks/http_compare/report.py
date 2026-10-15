import csv
import json
import math
import statistics
from html import escape
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
FRAMEWORK_LABELS = {
    "orionis-rsgi": "Orionis RSGI",
    "orionis-asgi": "Orionis ASGI",
    "fastapi": "FastAPI",
    "litestar": "Litestar",
    "starlette": "Starlette",
}


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


def render_throughput_svg(report: dict[str, Any], workers: int) -> str:
    """
    Render a ranked throughput chart from successful per-configuration medians.

    Parameters
    ----------
    report : dict[str, Any]
        Comparison report with settings, environment, and aggregated results.
    workers : int
        Worker count to display without mixing different configurations.

    Returns
    -------
    str
        Standalone SVG with accessible labels and measurement context.

    Raises
    ------
    ValueError
        If the selected comparison is incomplete, failed, or has invalid rates.
    """
    settings = report["settings"]
    expected = set(settings["frameworks"])
    rows = [row for row in report["results"] if row["workers"] == workers]
    if (
        report.get("error")
        or not expected
        or len(rows) != len(expected)
        or {row["framework"] for row in rows} != expected
        or any(row["status"] != "ok" or row["errors"] for row in rows)
    ):
        error_msg = "Throughput charts require a complete, error-free comparison"
        raise ValueError(error_msg)
    rates = [row["requests_per_second"] for row in rows]
    if any(
        isinstance(rate, bool)
        or not isinstance(rate, int | float)
        or not math.isfinite(rate)
        or rate <= 0
        for rate in rates
    ):
        error_msg = "Throughput chart rates must be finite and greater than zero"
        raise ValueError(error_msg)
    rows.sort(key=lambda row: (-row["requests_per_second"], row["framework"]))

    raw_step = max(rates) / 4
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = math.ceil(raw_step / magnitude) * magnitude
    upper = step * 4
    precision = max(0, -math.floor(math.log10(step)))
    plot_left, plot_width, plot_top, row_height = 150, 620, 100, 60
    plot_bottom = plot_top + len(rows) * row_height - 12
    height = plot_bottom + 108
    title = f"Throughput with {workers} worker{'s' if workers != 1 else ''}"
    description = "Successful HTTP 200 requests per second. Higher is better."
    lines = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="900" height="{height}" viewBox="0 0 900 {height}" '
            'role="img" aria-labelledby="title description">'
        ),
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="description">{description}</desc>',
        "<style>",
        "text { font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; }",
        ".heading { fill: #f0f6fc; font-size: 17px; font-weight: 600; }",
        ".label { fill: #c9d1d9; font-size: 13px; }",
        ".muted { fill: #8b949e; font-size: 11px; }",
        ".grid { stroke: #30363d; stroke-dasharray: 3 5; }",
        ".bar { fill: #245493; }",
        "</style>",
        f'<rect width="900" height="{height}" rx="8" fill="#0d1117"/>',
        f'<text class="heading" x="30" y="32">{escape(title)}</text>',
        f'<text class="label" x="30" y="57">{description}</text>',
    ]
    for tick in range(5):
        x = plot_left + plot_width * tick / 4
        lines.extend([
            (
                f'<line class="grid" x1="{x:.2f}" y1="{plot_top - 8}" '
                f'x2="{x:.2f}" y2="{plot_bottom}"/>'
            ),
            (
                f'<text class="muted" x="{x:.2f}" y="{plot_bottom + 24}" '
                f'text-anchor="middle">{step * tick:,.{precision}f}</text>'
            ),
        ])
    for index, row in enumerate(rows):
        framework = row["framework"]
        label = FRAMEWORK_LABELS.get(framework, framework)
        rate = row["requests_per_second"]
        width = rate / upper * plot_width
        y = plot_top + index * row_height
        lines.extend([
            f'<g data-framework="{escape(framework)}">',
            f"<title>{escape(label)}: {rate:,.2f} requests/s</title>",
            (
                f'<text class="label" x="{plot_left - 12}" y="{y + 27}" '
                f'text-anchor="end">{escape(label)}</text>'
            ),
            (
                f'<rect class="bar" x="{plot_left}" y="{y}" '
                f'width="{width:.2f}" height="44" rx="6"/>'
            ),
            (
                f'<text class="label" x="{plot_left + width + 10:.2f}" '
                f'y="{y + 27}">{rate:,.2f}</text>'
            ),
            "</g>",
        ])
    environment = report["environment"]
    measurement = (
        f"Median of {settings['repetitions']} x "
        f"{settings['duration_seconds']:g}s | "
        f"{settings['connections']} connections | "
        f"{settings['warmup_seconds']:g}s warmup"
    )
    context = (
        f"Python {environment['python']} | "
        f"Granian {environment['versions']['granian']} | "
        f"Commit {environment.get('commit', 'unknown')[:7]} | "
        f"{environment.get('recorded_at', 'unknown').split('T')[0]}"
    )
    for offset, text in (
        (54, measurement),
        (74, context),
        (
            94,
            "Hello World microbenchmark; GitHub-hosted runner performance varies.",
        ),
    ):
        lines.append(
            f'<text class="muted" x="30" y="{plot_bottom + offset}">'
            f"{escape(text)}</text>",
        )
    lines.append("</svg>")
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
