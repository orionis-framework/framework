import csv
import json
import math
import os
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import Mock, patch
from benchmarks.http_compare import run as compare_run
from benchmarks.http_compare.client import parse_measurement
from benchmarks.http_compare.report import METRICS, aggregate_samples, write_reports

def _measurement() -> dict[str, Any]:
    """
    Build realistic oha output with HTTP and transport failures.

    Returns
    -------
    dict[str, Any]
        Raw payload with mixed outcomes, timings, and an inflated client rate.
    """
    # Inflate the client rate to prove throughput is recomputed from HTTP 200.
    return {
        "statusCodeDistribution": {"200": 100, "404": 7, "500": 2},
        "errorDistribution": {"connection refused": 3, "timeout": 4},
        "summary": {"total": 2.5, "average": 0.012, "requestsPerSec": 999999},
        "latencyPercentiles": {"p50": 0.008, "p95": 0.03, "p99": 0.05},
    }

def _successful_runs() -> list[dict[str, int | float]]:
    """
    Build three successful runs with unequal load and latency distributions.

    Returns
    -------
    list[dict[str, int | float]]
        Normalized runs with distinct durations, rates, and latency statistics.
    """
    # Unequal durations expose accidental pooling or weighted averages.
    samples = []
    for requests, elapsed, mean, p50, p95, p99 in (
        (10, 1, 0.001, 0.0005, 0.002, 0.003),
        (1000, 5, 0.09, 0.08, 0.095, 0.099),
        (100, 1, 0.01, 0.005, 0.02, 0.03),
    ):
        samples.append(parse_measurement({
            "statusCodeDistribution": {"200": requests},
            "errorDistribution": {},
            "summary": {"total": elapsed, "average": mean},
            "latencyPercentiles": {"p50": p50, "p95": p95, "p99": p99},
        }))
    return samples

class TestMeasurements(unittest.TestCase):
    """Verify successful throughput, latency units, and independent samples."""

    def test_success_throughput_and_latency_units(self) -> None:
        """
        Verify HTTP 200 throughput and latency conversion to milliseconds.

        Returns
        -------
        None
            Assert exact counts, elapsed time, successful throughput, and latencies.
        """
        # Compare the complete shape so missing or additional metrics are visible.
        self.assertEqual(parse_measurement(_measurement()), {
            "requests": 100,
            "errors": 16,
            "elapsed_seconds": 2.5,
            "requests_per_second": 40,
            "mean_latency_ms": 12,
            "p50_latency_ms": 8,
            "p95_latency_ms": 30,
            "p99_latency_ms": 50,
        })

    def test_measurement_rejects_absent_successes_or_zero_elapsed(self) -> None:
        """
        Reject runs that cannot define successful-request throughput.

        Returns
        -------
        None
            Assert rejection of absent HTTP 200 responses and zero elapsed time.
        """
        # Keep one rate component valid while invalidating the other.
        for statuses, elapsed in (
            ({}, 2.5),
            ({"201": 100}, 2.5),
            ({"200": 0}, 2.5),
            ({"200": 100}, 0),
        ):
            with self.subTest(statuses=statuses, elapsed=elapsed):
                raw = _measurement()
                raw["statusCodeDistribution"] = statuses
                raw["summary"]["total"] = elapsed
                with self.assertRaises(ValueError):
                    parse_measurement(raw)

    def test_measurement_rejects_invalid_numbers(self) -> None:
        """
        Reject invalid numeric counts and timings.

        Returns
        -------
        None
            Assert rejection of invalid values and fractional request counts.
        """
        # Cover every numeric payload field, not only successful-request counts.
        fields = (
            ("statusCodeDistribution", "200"),
            ("statusCodeDistribution", "500"),
            ("errorDistribution", "timeout"),
            ("summary", "total"),
            ("summary", "average"),
            ("latencyPercentiles", "p50"),
            ("latencyPercentiles", "p95"),
            ("latencyPercentiles", "p99"),
        )
        for section, field in fields:
            for value in (-1, math.nan, math.inf, -math.inf, True, "1"):
                with self.subTest(section=section, field=field, value=value):
                    raw = _measurement()
                    raw[section][field] = value
                    with self.assertRaises(ValueError):
                        parse_measurement(raw)
        # Timings may be fractional, but status and error counts must be integral.
        for section, field in fields[:3]:
            with self.subTest(section=section, field=field, value=1.5):
                raw = _measurement()
                raw[section][field] = 1.5
                with self.assertRaises(ValueError):
                    parse_measurement(raw)

    def test_statistics_are_medians_of_individual_runs(self) -> None:
        """
        Verify equally weighted medians across independent runs.

        Returns
        -------
        None
            Assert per-run medians and totals that exclude duration weighting.
        """
        result = aggregate_samples(_successful_runs())

        # The arithmetic mean of the rates is 103.33; pooled throughput is 158.57.
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["requests_per_second"], 100)
        self.assertEqual(result["mean_latency_ms"], 10)
        self.assertEqual(result["p50_latency_ms"], 5)
        self.assertEqual(result["p95_latency_ms"], 20)
        self.assertEqual(result["p99_latency_ms"], 30)
        self.assertEqual(result["requests"], 1110)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(len(result["samples"]), 3)

    def test_one_failing_run_invalidates_comparative_metrics(self) -> None:
        """
        Verify that one failing run invalidates all comparative metrics.

        Returns
        -------
        None
            Assert retained samples and diagnostics without published medians.
        """
        # Mix healthy and errored samples to prevent cherry-picking valid runs.
        runs = _successful_runs()
        runs[1] = parse_measurement(_measurement())
        result = aggregate_samples(runs)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["requests"], 210)
        self.assertEqual(result["errors"], 16)
        self.assertEqual(result["samples"][1]["requests_per_second"], 40)
        self.assertIn("errors", result["reason"])
        for metric in METRICS:
            self.assertNotIn(metric, result)

    def test_empty_measurements_cannot_publish_a_result(self) -> None:
        """
        Require at least one measured run before aggregation.

        Returns
        -------
        None
            Assert that an empty sample sequence raises ``ValueError``.
        """
        # An empty run must fail rather than publish a success-shaped result.
        with self.assertRaises(ValueError):
            aggregate_samples([])

class TestBenchmarkRunner(unittest.TestCase):
    """Verify equal server settings, warmup isolation, and worker cleanup."""

    def test_frameworks_share_server_settings(self) -> None:
        """
        Verify identical server settings across framework configurations.

        Returns
        -------
        None
            Assert that only the application target and native interface differ.
        """
        # Normalize only permitted differences before comparing full commands.
        reference = compare_run.server_command(
            compare_run.FRAMEWORKS["orionis-asgi"], 2, 8000,
        )
        for framework in compare_run.FRAMEWORKS.values():
            with self.subTest(framework=framework.name):
                command = compare_run.server_command(framework, 2, 8000)
                self.assertEqual(command[4], framework.target)
                interface_index = command.index("--interface") + 1
                self.assertEqual(command[interface_index], framework.interface)
                command[4] = reference[4]
                command[interface_index] = reference[interface_index]
                self.assertEqual(command, reference)

    def test_warmup_is_retained_but_excluded_from_measured_results(self) -> None:
        """
        Verify that retained warmup data cannot affect measured results.

        Returns
        -------
        None
            Assert measured totals, medians, run durations, and server cleanup.
        """
        # Make warmup much faster than measured runs to expose contamination.
        raw = _measurement()
        raw["statusCodeDistribution"] = {"200": 1000000}
        raw["errorDistribution"] = {}
        raw["summary"]["total"] = 2
        warmup = parse_measurement(raw)
        measured = _successful_runs()
        process = Mock()
        process.poll.return_value = None
        args = Namespace(warmup=2, duration=10, connections=100, repetitions=3)
        row = {"status": "pending"}

        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "logs").mkdir()
            (output / "raw").mkdir()
            with (
                patch.object(compare_run.subprocess, "Popen", return_value=process),
                patch.object(compare_run, "wait_until_ready"),
                patch.object(compare_run, "check_workers") as check,
                patch.object(compare_run, "stop_server") as stop,
                patch.object(
                    compare_run, "run_load", side_effect=[warmup, *measured],
                ) as load,
            ):
                compare_run.benchmark_case(
                    compare_run.FRAMEWORKS["starlette"], 1, args,
                    output / "oha", output, [], row,
                )

        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["warmup"]["requests"], 1000000)
        self.assertEqual(row["requests"], 1110)
        self.assertEqual(row["requests_per_second"], 100)
        self.assertEqual(row["samples"], measured)
        self.assertEqual(
            [call.args[2] for call in load.call_args_list], [2, 10, 10, 10],
        )
        self.assertEqual(check.call_count, 4)
        stop.assert_called_once_with(process, {})

    def test_cleanup_stops_known_workers_after_supervisor_has_exited(self) -> None:
        """
        Verify cleanup of a known Windows worker after its supervisor exits.

        Returns
        -------
        None
            Assert termination, kill escalation, and reaping of the owned worker.
        """
        # Model an orphan that survives graceful termination and requires a kill.
        process = Mock(pid=1234)
        worker = Mock(pid=5678)
        known = {worker.pid: worker}
        with (
            patch.object(compare_run.sys, "platform", "win32"),
            patch.object(
                compare_run.psutil, "Process",
                side_effect=compare_run.psutil.NoSuchProcess(process.pid),
            ),
            patch.object(
                compare_run.psutil, "wait_procs",
                side_effect=[([], [worker]), ([worker], [])],
            ) as wait,
        ):
            compare_run.stop_server(process, known)

        worker.terminate.assert_called_once_with()
        worker.kill.assert_called_once_with()
        self.assertEqual(wait.call_args_list[0].args[0], [worker])
        self.assertEqual(wait.call_args_list[1].args[0], [worker])
        process.wait.assert_called_once_with(timeout=5)

    def test_worker_markers_require_a_living_owned_process(self) -> None:
        """
        Reject startup markers without a live owned worker.

        Returns
        -------
        None
            Assert rejection of both dead workers and unrelated process IDs.
        """
        # A live foreign PID must fail just as a dead owned worker does.
        for scenario, marker_pid in (("dead", 5678), ("foreign", 9999)):
            with self.subTest(scenario=scenario), TemporaryDirectory() as temporary:
                ready = Path(temporary)
                (ready / str(marker_pid)).touch()
                process = Mock(pid=1234)
                process.poll.return_value = None
                worker = Mock(pid=5678)
                worker.is_running.return_value = scenario != "dead"
                parent = Mock()
                parent.children.return_value = [worker]
                with (
                    patch.object(compare_run.psutil, "Process", return_value=parent),
                    self.assertRaisesRegex(RuntimeError, str(marker_pid)),
                ):
                    compare_run.check_workers(process, ready, 1, {})

    def test_main_preserves_partial_samples_and_continues(self) -> None:
        """
        Verify partial failure reporting and continuation to subsequent cases.

        Returns
        -------
        None
            Assert failure status, retained samples, and later valid results.
        """
        # Keep actual CLI orchestration and artifact persistence under test.
        samples = _successful_runs()
        environment = {
            "os": "CI test host", "python": "3.14.8",
            "versions": {"granian": "2.8.4"},
        }

        def benchmark(
            framework: compare_run.Framework,
            _workers: int,
            _args: Namespace,
            _oha: Path,
            _output: Path,
            _commands: list[dict[str, Any]],
            row: dict[str, Any],
        ) -> None:
            """
            Simulate a late worker failure or aggregate a healthy configuration.

            Parameters
            ----------
            framework : compare_run.Framework
                Framework selecting the simulated execution outcome.
            _workers : int
                Requested worker count, unused by the simulation.
            _args : Namespace
                Parsed load settings, unused by the simulation.
            _oha : Path
                Load-generator path, unused by the simulation.
            _output : Path
                Artifact directory, unused by the simulation.
            _commands : list[dict[str, Any]]
                Invocation log, unused by the simulation.
            row : dict[str, Any]
                Result row to mutate before returning or raising.

            Returns
            -------
            None
                Update a healthy row with aggregate metrics.

            Raises
            ------
            RuntimeError
                If FastAPI is selected, after storing partial measurements.
            """
            # Leave partial metrics behind to exercise late-failure cleanup.
            if framework.name == "fastapi":
                row["samples"] = [samples[0]]
                row["requests_per_second"] = 1234
                error_msg = "worker exited during the second execution"
                raise RuntimeError(error_msg)
            row.update(aggregate_samples(samples))

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            with (
                patch.object(
                    compare_run, "collect_environment", return_value=environment,
                ),
                patch.object(
                    compare_run, "resolve_oha", return_value=Path(temporary) / "oha",
                ),
                patch.object(compare_run.random.Random, "shuffle"),
                patch.object(
                    compare_run, "benchmark_case", side_effect=benchmark, autospec=True,
                ) as run,
                patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}),
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                exit_code = compare_run.main([
                    "--workers", "1", "--frameworks", "fastapi", "starlette",
                    "--output-dir", str(output),
                ])
            saved = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            markdown = (output / "summary.md").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 1)
        self.assertEqual(run.call_count, 2)
        failed, successful = saved["results"]
        self.assertEqual(failed["framework"], "fastapi")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["samples"], [samples[0]])
        self.assertIn("worker exited", failed["reason"])
        for metric in METRICS:
            self.assertNotIn(metric, failed)
        self.assertEqual(successful["framework"], "starlette")
        self.assertEqual(successful["status"], "ok")
        self.assertEqual(successful["requests_per_second"], 100)
        self.assertIn("| fastapi | asgi | 1 | failed | - | - | - | - | - |", markdown)
        self.assertIn("| starlette | asgi | 1 | ok | 100.00 |", markdown)

class TestComparisonReports(unittest.TestCase):
    """Verify that every artifact publishes the same comparative results."""

    def test_artifacts_preserve_valid_data_and_label_failures(self) -> None:
        """
        Verify consistent artifacts with explicit failed-result placeholders.

        Returns
        -------
        None
            Assert matching JSON, CSV, Markdown, and environment metadata.
        """
        # Pair a valid row with an errored row to expose invented failure metrics.
        good = {
            "framework": "starlette", "interface": "asgi", "workers": 1,
            **aggregate_samples(_successful_runs()),
        }
        failed = {
            "framework": "fastapi", "interface": "asgi", "workers": 2,
            **aggregate_samples([parse_measurement(_measurement())]),
        }
        report = {
            "settings": {
                "connections": 100, "warmup_seconds": 2,
                "repetitions": 3, "duration_seconds": 10,
            },
            "environment": {
                "os": "Ubuntu CI", "cpu": "CI CPU", "logical_cpus": 4,
                "python": "3.14.8", "commit": "abc123", "dirty": False,
                "run_url": "https://example.org/runs/123",
                "versions": {"granian": "2.8.4", "oha": "1.16.0"},
            },
            "results": [good, failed],
        }

        # Read every artifact before the temporary workspace is released.
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            rendered = write_reports(output, report)
            saved_report = json.loads(
                (output / "summary.json").read_text(encoding="utf-8"),
            )
            saved_environment = json.loads(
                (output / "environment.json").read_text(encoding="utf-8"),
            )
            markdown = (output / "summary.md").read_text(encoding="utf-8")
            with (output / "summary.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))

        self.assertEqual(saved_report, report)
        self.assertEqual(saved_environment, report["environment"])
        self.assertEqual(markdown, rendered)
        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(float(rows[0]["requests_per_second"]), 100)
        self.assertEqual(float(rows[0]["p99_latency_ms"]), 30)
        self.assertEqual(rows[1]["status"], "failed")
        self.assertEqual(rows[1]["errors"], "16")
        self.assertEqual(rows[1]["reason"], failed["reason"])
        for column in METRICS:
            self.assertEqual(rows[1][column], "")
        self.assertIn(
            "| starlette | asgi | 1 | ok | 100.00 | 10.00 | "
            "5.00 | 20.00 | 30.00 | 0 |",
            markdown,
        )
        self.assertIn(
            "| fastapi | asgi | 2 | failed | - | - | - | - | - | 16 |",
            markdown,
        )
        self.assertIn(failed["reason"], markdown)
        self.assertIn("- commit: abc123", markdown)
        self.assertIn("- granian: 2.8.4", markdown)
