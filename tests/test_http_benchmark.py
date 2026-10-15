import json
import os
import sys
from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from orionis.test import TestCase

# Import standalone CI scripts without retaining changes to the module registry.
_SCRIPTS = Path(__file__).resolve().parents[1] / ".github" / "scripts"
with (
    patch.object(sys, "path", [str(_SCRIPTS), *sys.path]),
    patch.dict(sys.modules),
):
    benchmark_http = import_module("benchmark_http")
    summarize_benchmarks = import_module("summarize_benchmarks")


def _measurement() -> dict[str, dict[str, int | float]]:
    """
    Build a load-test payload with successful and failing request outcomes.

    Returns
    -------
    dict[str, dict[str, int | float]]
        Status counts, transport errors, elapsed time, and latency statistics.
    """
    # Inflate the client rate to verify that successful throughput is recomputed.
    return {
        "statusCodeDistribution": {"200": 100, "404": 7, "500": 2},
        "errorDistribution": {"connection refused": 3, "timeout": 4},
        "summary": {"total": 2.5, "average": 0.012, "requestsPerSec": 999999},
        "latencyPercentiles": {"p95": 0.05},
    }


def _report(platform_name: str) -> dict[str, Any]:
    """
    Build platform results with explicit unsupported Windows worker counts.

    Parameters
    ----------
    platform_name : str
        Platform label to include in the report and its environment metadata.

    Returns
    -------
    dict[str, Any]
        Platform report containing worker results, load settings, and metadata.
    """
    # Keep unsupported configurations free of synthetic numeric measurements.
    results = []
    for workers in range(1, 5):
        if platform_name == "Windows" and workers > 1:
            results.append(
                {
                    "workers": workers,
                    "status": "unsupported",
                    "reason": benchmark_http.WINDOWS_LIMIT,
                },
            )
        else:
            results.append(
                {
                    "workers": workers,
                    "status": "ok",
                    "requests_per_second": workers * 125.5,
                    "requests": workers * 3765,
                    "errors": 0,
                    "mean_latency_ms": 1.25,
                    "p95_latency_ms": 2.5,
                },
            )
    # Mirror the producer's schema so rendering uses realistic runner metadata.
    return {
        "schema_version": 1,
        "platform": platform_name,
        "environment": {
            "os": f"{platform_name} CI image",
            "architecture": "x86_64",
            "cpu": "CI test CPU",
            "logical_cpus": 4,
            "python": "3.14.6",
            "orionis": "0.912.0",
            "granian": "2.8.3",
            "oha": "1.16.0",
            "commit": "0123456789abcdef",
            "run_url": "https://github.com/example/framework/actions/runs/123",
        },
        "settings": {
            "duration_seconds": 10,
            "warmup_seconds": 2,
            "connections": 100,
            "repetitions": 3,
            "interface": "rsgi",
            "http": "1.1",
            "loop": "asyncio",
        },
        "results": results,
    }


def _consolidate(
    reports: list[dict[str, Any]],
) -> tuple[int, dict[str, Any], str, str, str]:
    """
    Run the consolidation CLI and collect its persisted and published output.

    Parameters
    ----------
    reports : list[dict[str, Any]]
        Platform reports to write as downloaded benchmark artifacts.

    Returns
    -------
    exit_code : int
        Consolidation command exit status.
    combined : dict[str, Any]
        Parsed combined JSON report.
    markdown : str
        Persisted Markdown report.
    summary : str
        Actions job-summary contents.
    stdout : str
        Captured command output.
    """
    # Keep artifacts and the Actions summary inside a disposable workspace.
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        inputs = root / "input"
        output = root / "output"
        summary = root / "step-summary.md"
        # Recreate the per-platform download layout consumed by the CLI.
        for report in reports:
            artifact = inputs / report["platform"]
            artifact.mkdir(parents=True)
            (artifact / "report.json").write_text(
                json.dumps(report),
                encoding="utf-8",
            )
        stdout = StringIO()
        # Exercise CLI parsing and summary publishing without leaking globals.
        with (
            patch.object(
                sys,
                "argv",
                [
                    "summarize_benchmarks.py",
                    "--input-dir",
                    str(inputs),
                    "--output-dir",
                    str(output),
                ],
            ),
            patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}),
            redirect_stdout(stdout),
        ):
            exit_code = summarize_benchmarks.main()
        # Read every output channel before the temporary workspace is removed.
        return (
            exit_code,
            json.loads((output / "report.json").read_text(encoding="utf-8")),
            (output / "report.md").read_text(encoding="utf-8"),
            summary.read_text(encoding="utf-8"),
            stdout.getvalue(),
        )


class TestHttpBenchmark(TestCase):
    """Verify successful-throughput accounting and published CI reports."""

    def testThroughputCountsOnlyHttp200OverActualElapsedTime(self) -> None:
        """
        Verify throughput excludes HTTP and transport failures.

        Returns
        -------
        None
            Assert successful counts, elapsed-time throughput, and latency units.
        """
        # Recompute throughput from successes, not the inflated client estimate.
        measured = benchmark_http.parse_measurement(_measurement())

        self.assertEqual(measured["requests"], 100)
        self.assertEqual(measured["elapsed_seconds"], 2.5)
        self.assertEqual(measured["requests_per_second"], 40)
        self.assertEqual(measured["errors"], 16)
        self.assertEqual(measured["mean_latency_ms"], 12)
        self.assertEqual(measured["p95_latency_ms"], 50)

    def testMeasurementRejectsMissingSuccessesOrNonpositiveElapsed(self) -> None:
        """
        Reject measurements without successful requests or positive elapsed time.

        Returns
        -------
        None
            Assert a ValueError for empty successes and nonpositive elapsed time.
        """
        # Exercise each invalid rate component while keeping the other valid.
        for successes, elapsed in ((0, 2.5), (100, 0), (100, -2.5)):
            with self.subTest(successes=successes, elapsed=elapsed):
                # Isolate payload mutations between invalid measurement cases.
                raw = _measurement()
                raw["statusCodeDistribution"]["200"] = successes
                raw["summary"]["total"] = elapsed
                with self.assertRaises(ValueError):
                    benchmark_http.parse_measurement(raw)

    def testUnsupportedWorkerCountsHaveNoInventedMeasurements(self) -> None:
        """
        Verify unsupported Windows workers contain no invented measurements.

        Returns
        -------
        None
            Assert only the supported worker publishes numeric measurements.
        """
        # Retain the measured single worker alongside explicit unsupported rows.
        markdown = summarize_benchmarks.render_report([_report("Windows")])

        self.assertIn("| Windows | 1 | ok | 125.50 |", markdown)
        # Require placeholder metrics and an explanation for unsupported workers.
        for workers in (2, 3, 4):
            with self.subTest(workers=workers):
                row = next(
                    line
                    for line in markdown.splitlines()
                    if line.startswith(f"| Windows | {workers} |")
                )
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                self.assertEqual(cells[2], "unsupported")
                self.assertEqual(cells[3:], ["-"] * 5)
                self.assertIn(f"Workers {workers} (unsupported):", markdown)
        self.assertIn(benchmark_http.WINDOWS_LIMIT, markdown)

    def testMissingPlatformsFailWhilePreservingAvailableResults(self) -> None:
        """
        Preserve available artifacts while failing an incomplete platform matrix.

        Returns
        -------
        None
            Assert failure status and consistent JSON, Markdown, and job output.
        """
        # Simulate valid Linux artifacts with both other platform jobs missing.
        available = _report("Linux")
        exit_code, combined, markdown, summary, stdout = _consolidate([available])

        # Require an explicit failure without discarding valid measurements.
        self.assertEqual(exit_code, 1)
        self.assertEqual(combined["platforms"], [available])
        self.assertIn(
            "Missing platform reports: Windows, macOS",
            combined["errors"],
        )
        self.assertIn("## Incomplete report", markdown)
        self.assertIn("Missing platform reports: Windows, macOS", markdown)
        self.assertIn("| Linux | 4 | ok | 502.00 |", markdown)
        self.assertEqual(summary, markdown)
        self.assertIn(markdown, stdout)

    def testCompleteMatrixPublishesEnvironmentAndLoadSettings(self) -> None:
        """
        Verify a complete platform matrix retains reproducibility metadata.

        Returns
        -------
        None
            Assert success, complete platform reports, and matching output.
        """
        # Include Windows' documented worker limitation in the complete matrix.
        platforms = ("Linux", "Windows", "macOS")
        reports = [_report(platform_name) for platform_name in platforms]
        exit_code, combined, markdown, summary, stdout = _consolidate(reports)

        self.assertEqual(exit_code, 0)
        self.assertEqual(combined["errors"], [])
        self.assertEqual(
            {report["platform"] for report in combined["platforms"]},
            set(platforms),
        )
        # Require each platform's identifying metadata in the published output.
        for platform_name in platforms:
            self.assertIn(f"## {platform_name}", stdout)
            self.assertIn(f"- os: {platform_name} CI image", stdout)
        # Preserve load settings, runtime versions, and source revision details.
        for detail in (
            "100 connections; 2s warmup; 3 x 10s measured per worker count.",
            "- cpu: CI test CPU",
            "- logical_cpus: 4",
            "- python: 3.14.6",
            "- orionis: 0.912.0",
            "- granian: 2.8.3",
            "- oha: 1.16.0",
            "- commit: 0123456789abcdef",
            "https://github.com/example/framework/actions/runs/123",
        ):
            self.assertIn(detail, stdout)
        # Keep persisted Markdown, the Actions summary, and console output aligned.
        self.assertEqual(summary, markdown)
        self.assertIn(markdown, stdout)
