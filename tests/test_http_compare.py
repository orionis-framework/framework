import csv
import json
import math
import os
import unittest
from argparse import Namespace
from contextlib import chdir, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import Mock, call, patch
from defusedxml import ElementTree
from benchmarks.http_compare import run as compare_run
from benchmarks.http_compare.apps import orionis as orionis_benchmark
from benchmarks.http_compare.client import parse_measurement
from benchmarks.http_compare.report import (
    METRICS,
    aggregate_samples,
    render_throughput_svg,
    write_reports,
)

def _measurement() -> dict[str, Any]:
    """
    Build an oha payload with HTTP errors and transport failures.

    Returns
    -------
    dict[str, Any]
        Mixed outcomes and timings with a deliberately inflated client rate.
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
    Build three normalized runs with unequal durations and latencies.

    Returns
    -------
    list[dict[str, int | float]]
        Successful per-run measurements for unweighted-median assertions.
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

def _probe_connection(worker_pid: int) -> Mock:
    """
    Mock two text responses followed by a worker-identity response.

    Parameters
    ----------
    worker_pid : int
        Process ID returned by the worker-discovery response.

    Returns
    -------
    Mock
        Persistent HTTP connection yielding the three prepared responses.
    """
    responses = []
    for body in (b"Hello World", b"Hello World", str(worker_pid).encode("ascii")):
        response = Mock(status=200, version=11, will_close=False)
        response.read.return_value = body
        response.getheader.return_value = "text/plain; charset=utf-8"
        responses.append(response)
    connection = Mock()
    connection.getresponse.side_effect = responses
    return connection

def _chart_report() -> dict[str, Any]:
    """
    Build a synthetic five-framework throughput comparison.

    Returns
    -------
    dict[str, Any]
        Complete chart input with fixture values, not published measurements.
    """
    rates = {
        "fastapi": 17200,
        "orionis-rsgi": 21050,
        "starlette": 29800,
        "litestar": 20900,
        "orionis-asgi": 21100,
    }
    return {
        "settings": {
            "frameworks": list(rates), "workers": [3],
            "connections": 100, "warmup_seconds": 2,
            "repetitions": 3, "duration_seconds": 10,
        },
        "environment": {
            "python": "3.14.8", "commit": "abc123456",
            "recorded_at": "2026-10-15T16:00:00+00:00",
            "versions": {"granian": "2.8.4"},
        },
        "results": [
            {
                "framework": name,
                "interface": "rsgi" if name == "orionis-rsgi" else "asgi",
                "workers": 3,
                **aggregate_samples(_successful_runs()),
                "requests_per_second": rate,
            }
            for name, rate in rates.items()
        ],
    }

class TestMeasurements(unittest.TestCase):
    """Verify successful throughput, latency units, and independent samples."""

    def test_success_throughput_and_latency_units(self) -> None:
        """
        Verify HTTP 200 throughput, error counts, and millisecond latencies.

        Returns
        -------
        None
            This test does not return a value.
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
        Verify that missing successes or zero elapsed time invalidate a run.

        Returns
        -------
        None
            This test does not return a value.
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
        Verify that measurements reject invalid counts and timings.

        Returns
        -------
        None
            This test does not return a value.
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
        Verify equally weighted per-run medians and accumulated totals.

        Returns
        -------
        None
            This test does not return a value.
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
        Verify that one failing run suppresses all comparative metrics.

        Returns
        -------
        None
            This test does not return a value.
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
        Verify that aggregation rejects an empty sample sequence.

        Returns
        -------
        None
            This test does not return a value.
        """
        # An empty run must fail rather than publish a success-shaped result.
        with self.assertRaises(ValueError):
            aggregate_samples([])

class TestOrionisApplication(unittest.TestCase):
    """Verify isolated routes and nonblocking worker readiness tracking."""

    def test_ready_kernel_is_published_without_fixed_delay(self) -> None:
        """
        Verify that a ready kernel publishes readiness without a fixed delay.

        Returns
        -------
        None
            This test does not return a value.
        """
        loop = Mock()
        app = Mock(isHttpReady=True)
        with (
            patch.dict(os.environ, {"BENCHMARK_READY_DIR": "enabled"}),
            patch.object(
                orionis_benchmark.asyncio, "get_running_loop", return_value=loop,
            ),
            patch.object(orionis_benchmark, "mark_ready") as ready,
        ):
            orionis_benchmark._track_readiness(app)

            loop.call_soon.assert_called_once()
            loop.call_later.assert_not_called()
            publish = loop.call_soon.call_args.args[0]
            ready.assert_not_called()

            publish()

            ready.assert_called_once_with()
            loop.call_later.assert_not_called()

    def test_slow_kernel_is_not_published_before_it_is_ready(self) -> None:
        """
        Verify that readiness retries stop once the HTTP kernel is ready.

        Returns
        -------
        None
            This test does not return a value.
        """
        loop = Mock()
        app = Mock(isHttpReady=False)
        with (
            patch.dict(os.environ, {"BENCHMARK_READY_DIR": "enabled"}),
            patch.object(
                orionis_benchmark.asyncio, "get_running_loop", return_value=loop,
            ),
            patch.object(orionis_benchmark, "mark_ready") as ready,
        ):
            orionis_benchmark._track_readiness(app)
            loop.call_soon.assert_called_once()
            publish = loop.call_soon.call_args.args[0]

            publish()

            ready.assert_not_called()
            loop.call_later.assert_called_once_with(0.01, publish)

            app.isHttpReady = True
            publish()

            ready.assert_called_once_with()
            loop.call_later.assert_called_once_with(0.01, publish)

    def test_standalone_startup_does_not_schedule_tracking(self) -> None:
        """
        Verify that standalone startup skips benchmark readiness tracking.

        Returns
        -------
        None
            This test does not return a value.
        """
        with (
            patch.dict(os.environ, {"BENCHMARK_READY_DIR": ""}),
            patch.object(orionis_benchmark.asyncio, "get_running_loop") as loop,
            patch.object(orionis_benchmark, "mark_ready") as ready,
        ):
            orionis_benchmark._track_readiness(Mock(isHttpReady=True))

        loop.assert_not_called()
        ready.assert_not_called()

    def test_factory_stages_static_routes_inside_isolated_directory(self) -> None:
        """
        Verify isolated route staging and startup with native directory paths.

        Returns
        -------
        None
            This test does not return a value.
        """
        app = Mock()
        app.withRouting.return_value = app
        app.withConfigApp.return_value = app
        app.on.return_value = app
        app.create.return_value = app
        source = Path(orionis_benchmark.__file__).parent / "routes" / "web.py"
        with (
            TemporaryDirectory() as temporary,
            chdir(temporary),
            patch.object(
                orionis_benchmark, "Application", return_value=app,
            ) as application,
        ):
            result = orionis_benchmark.create_application()
            # Windows cwd may retain an 8.3 alias for the temporary directory.
            directory = Path.cwd()
            self.assertTrue(directory.samefile(temporary))
            route_file = directory / f"_orionis_http_benchmark_{os.getpid()}.py"

            self.assertEqual(route_file.read_bytes(), source.read_bytes())
            application.assert_called_once_with(base_path=directory)
            app.withRouting.assert_called_once_with(api=route_file.name)
            app.withConfigApp.assert_called_once_with(
                env="production", debug=False, maintenance=False,
            )
            app.on.assert_called_once_with(
                orionis_benchmark.Lifespan.STARTUP,
                orionis_benchmark._track_readiness,
                runtime=orionis_benchmark.Runtime.HTTP,
            )
            app.create.assert_called_once_with()
            self.assertIs(result, app)

class TestBenchmarkRunner(unittest.TestCase):
    """Verify equal server settings, warmup isolation, and worker cleanup."""

    def test_frameworks_share_server_settings(self) -> None:
        """
        Verify equal server settings across framework configurations.

        Returns
        -------
        None
            This test does not return a value.
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

    def test_first_requests_prime_every_worker_before_readiness(self) -> None:
        """
        Verify that readiness requires real requests on every worker.

        Returns
        -------
        None
            This test does not return a value.
        """
        process = Mock()
        process.poll.return_value = None
        for workers in range(1, 5):
            with self.subTest(workers=workers), TemporaryDirectory() as temporary:
                ready = Path(temporary)
                pids = list(range(5678, 5678 + workers))
                for pid in pids:
                    (ready / str(pid)).touch()
                visits = [pids[0], *pids] if workers > 1 else pids
                connections = [_probe_connection(pid) for pid in visits]
                with (
                    patch.object(compare_run, "track_children"),
                    patch.object(compare_run, "check_workers"),
                    patch.object(
                        compare_run.http.client, "HTTPConnection",
                        side_effect=connections,
                    ) as connect,
                    patch.object(compare_run.time, "sleep"),
                ):
                    compare_run.wait_until_ready(process, 8000, ready, workers, {})

                self.assertEqual(connect.call_count, len(visits))
                for connection in connections:
                    self.assertEqual(connection.request.call_args_list, [
                        call("GET", "/"),
                        call("GET", "/"),
                        call("GET", "/_benchmark/worker"),
                    ])
                    self.assertEqual(connection.getresponse.call_count, 3)
                    connection.close.assert_called_once_with()

    def test_missing_worker_times_out_before_measurements(self) -> None:
        """
        Verify that an unvisited live worker causes readiness to time out.

        Returns
        -------
        None
            This test does not return a value.
        """
        process = Mock()
        process.poll.return_value = None
        connection = _probe_connection(5678)
        with TemporaryDirectory() as temporary:
            ready = Path(temporary)
            for pid in (5678, 5679):
                (ready / str(pid)).touch()
            with (
                patch.object(compare_run, "track_children"),
                patch.object(compare_run, "check_workers"),
                patch.object(
                    compare_run.http.client, "HTTPConnection",
                    return_value=connection,
                ),
                patch.object(compare_run.time, "sleep"),
                patch.object(
                    compare_run.time, "monotonic", side_effect=[0, 0, 61],
                ),
                self.assertRaisesRegex(TimeoutError, "1/2"),
            ):
                compare_run.wait_until_ready(process, 8000, ready, 2, {})

        connection.close.assert_called_once_with()

    def test_probe_rejects_an_unowned_worker_identity(self) -> None:
        """
        Verify that readiness rejects worker identities outside the owned set.

        Returns
        -------
        None
            This test does not return a value.
        """
        process = Mock()
        process.poll.return_value = None
        connection = _probe_connection(9999)
        with TemporaryDirectory() as temporary:
            ready = Path(temporary)
            (ready / "5678").touch()
            with (
                patch.object(compare_run, "track_children"),
                patch.object(compare_run, "check_workers"),
                patch.object(
                    compare_run.http.client, "HTTPConnection",
                    return_value=connection,
                ),
                self.assertRaisesRegex(RuntimeError, "9999"),
            ):
                compare_run.wait_until_ready(process, 8000, ready, 1, {})

        connection.close.assert_called_once_with()

    def test_preparation_rejects_invalid_http_responses(self) -> None:
        """
        Verify probe status, payload, media type, and keep-alive checks.

        Returns
        -------
        None
            This test does not return a value.
        """
        for status, body, content_type, version, will_close in (
            (500, b"Hello World", "text/plain", 11, False),
            (200, b"Hello World\n", "text/plain", 11, False),
            (200, b"Hello World", "application/json", 11, False),
            (200, b"Hello World", "text/plain", 10, False),
            (200, b"Hello World", "text/plain", 11, True),
        ):
            with self.subTest(
                status=status, body=body, content_type=content_type,
                version=version, will_close=will_close,
            ):
                response = Mock(
                    status=status, version=version, will_close=will_close,
                )
                response.read.return_value = body
                response.getheader.return_value = content_type
                connection = Mock()
                connection.getresponse.return_value = response
                with self.assertRaises(RuntimeError):
                    compare_run._probe_response(connection, "/", b"Hello World")
                response.read.assert_called_once_with()

    def test_failed_preparation_never_starts_load(self) -> None:
        """
        Verify that failed preparation prevents load and cleans up the server.

        Returns
        -------
        None
            This test does not return a value.
        """
        process = Mock()
        args = Namespace(warmup=2, duration=10, connections=100, repetitions=3)
        row = {"status": "pending"}
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "logs").mkdir()
            with (
                patch.object(compare_run.subprocess, "Popen", return_value=process),
                patch.object(
                    compare_run, "wait_until_ready",
                    side_effect=TimeoutError("1/2 workers primed"),
                ),
                patch.object(compare_run, "run_load") as load,
                patch.object(compare_run, "stop_server") as stop,
                self.assertRaisesRegex(TimeoutError, "1/2"),
            ):
                compare_run.benchmark_case(
                    compare_run.FRAMEWORKS["orionis-rsgi"], 2, args,
                    output / "oha", output, [], row,
                )

        load.assert_not_called()
        stop.assert_called_once_with(process, {})
        self.assertNotIn("warmup", row)
        self.assertNotIn("samples", row)

    def test_warmup_is_retained_but_excluded_from_measured_results(self) -> None:
        """
        Verify that retained warmup samples never affect measured results.

        Returns
        -------
        None
            This test does not return a value.
        """
        self.assertEqual(compare_run.build_parser().parse_args([]).warmup, 2)
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
        order = Mock()

        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "logs").mkdir()
            (output / "raw").mkdir()
            with (
                patch.object(compare_run.subprocess, "Popen", return_value=process),
                patch.object(compare_run, "wait_until_ready") as prepare,
                patch.object(compare_run, "check_workers") as check,
                patch.object(compare_run, "stop_server") as stop,
                patch.object(
                    compare_run, "run_load", side_effect=[warmup, *measured],
                ) as load,
            ):
                order.attach_mock(prepare, "prepare")
                order.attach_mock(load, "load")
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
        self.assertEqual(
            [entry[0] for entry in order.mock_calls],
            ["prepare", "load", "load", "load", "load"],
        )
        self.assertEqual(check.call_count, 4)
        stop.assert_called_once_with(process, {})

    def test_cleanup_stops_known_workers_after_supervisor_has_exited(self) -> None:
        """
        Verify cleanup and kill escalation for an orphaned Windows worker.

        Returns
        -------
        None
            This test does not return a value.
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
        Verify that readiness markers identify live, owned workers.

        Returns
        -------
        None
            This test does not return a value.
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
        Verify that partial failures retain samples and allow later cases.

        Returns
        -------
        None
            This test does not return a value.
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
            Simulate a late FastAPI failure or aggregate healthy measurements.

            Parameters
            ----------
            framework : compare_run.Framework
                Framework whose name selects failure or success.
            _workers : int
                Worker count, unused by this test double.
            _args : Namespace
                Parsed settings, unused by this test double.
            _oha : Path
                Load-generator path, unused by this test double.
            _output : Path
                Output directory, unused by this test double.
            _commands : list[dict[str, Any]]
                Command log, unused by this test double.
            row : dict[str, Any]
                Result row populated with complete or partial measurements.

            Returns
            -------
            None
                Update the result row with successful aggregate metrics.

            Raises
            ------
            RuntimeError
                If FastAPI is selected, after recording one partial sample.
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
            charts = list(output.glob("throughput-*.svg"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(charts, [])
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

    def test_successful_main_writes_chart_from_saved_report(self) -> None:
        """
        Verify that a successful run saves charts matching its saved report.

        Returns
        -------
        None
            This test does not return a value.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            with (
                patch.object(compare_run.sys, "platform", "linux"),
                patch.object(
                    compare_run, "collect_environment",
                    return_value=_chart_report()["environment"],
                ),
                patch.object(
                    compare_run, "resolve_oha", return_value=Path(temporary) / "oha",
                ),
                patch.object(
                    compare_run, "benchmark_case",
                    side_effect=lambda *args: args[-1].update(
                        aggregate_samples(_successful_runs()),
                    ),
                ),
                patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}),
                redirect_stdout(StringIO()),
            ):
                exit_code = compare_run.main([
                    "--workers", "1", "2", "3", "4",
                    "--frameworks", "fastapi", "starlette",
                    "--output-dir", str(output),
                ])
            saved = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            charts = {
                path.name: path.read_text(encoding="utf-8")
                for path in output.glob("throughput-*.svg")
            }

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            set(charts),
            {f"throughput-{workers}-workers.svg" for workers in range(1, 5)},
        )
        for workers in range(1, 5):
            self.assertEqual(
                charts[f"throughput-{workers}-workers.svg"],
                render_throughput_svg(saved, workers),
            )
        self.assertIn(
            "Throughput with 1 worker</title>", charts["throughput-1-workers.svg"],
        )
        self.assertIn(
            "Throughput with 3 workers</title>", charts["throughput-3-workers.svg"],
        )

class TestThroughputCharts(unittest.TestCase):
    """Verify comparable, ranked, accessible SVG charts without invented data."""

    def test_svg_uses_sorted_three_worker_medians(self) -> None:
        """
        Verify SVG ranking, scaling, worker filtering, and benchmark context.

        Returns
        -------
        None
            This test does not return a value.
        """
        report = _chart_report()
        report["results"].append({
            **report["results"][0], "workers": 1, "requests_per_second": 999999,
        })
        svg = render_throughput_svg(report, 3)
        root = ElementTree.fromstring(svg)
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        groups = root.findall("svg:g", namespace)
        expected = [
            ("starlette", 29800), ("orionis-asgi", 21100),
            ("orionis-rsgi", 21050), ("litestar", 20900), ("fastapi", 17200),
        ]
        self.assertEqual(
            [group.attrib["data-framework"] for group in groups],
            [name for name, _ in expected],
        )
        for group, (_, rate) in zip(groups, expected, strict=True):
            bars = group.findall("svg:rect", namespace)
            self.assertEqual(len(bars), 1)
            self.assertAlmostEqual(
                float(bars[0].attrib["width"]), rate / 32000 * 620, places=2,
            )
            self.assertIn(f"{rate:,.2f}", "".join(group.itertext()))
        self.assertEqual(root.attrib["role"], "img")
        self.assertIn("Throughput with 3 workers", svg)
        self.assertIn("HTTP 200 requests per second. Higher is better.", svg)
        self.assertIn(">32,000</text>", svg)
        self.assertIn("Median of 3 x 10s | 100 connections | 2s warmup", svg)
        self.assertIn("Python 3.14.8 | Granian 2.8.4 | Commit abc1234", svg)
        self.assertIn("2026-10-15", svg)
        self.assertNotIn("999,999", svg)

    def test_chart_rejects_incomplete_failed_or_errored_results(self) -> None:
        """
        Verify that charts reject incomplete or failed comparison data.

        Returns
        -------
        None
            This test does not return a value.
        """
        for scenario in ("missing", "duplicate", "failed", "errors", "setup"):
            with self.subTest(scenario=scenario):
                report = _chart_report()
                if scenario == "missing":
                    report["results"].pop()
                elif scenario == "duplicate":
                    report["results"].append(report["results"][0])
                elif scenario == "failed":
                    report["results"][0]["status"] = "failed"
                elif scenario == "errors":
                    report["results"][0]["errors"] = 1
                else:
                    report["error"] = "Setup failed"
                with self.assertRaisesRegex(ValueError, "complete, error-free"):
                    render_throughput_svg(report, 3)
        with self.assertRaisesRegex(ValueError, "complete, error-free"): # NOSONAR
            render_throughput_svg(_chart_report(), 4)

    def test_chart_rejects_invalid_rates(self) -> None:
        """
        Verify that charts reject invalid numeric throughput rates.

        Returns
        -------
        None
            This test does not return a value.
        """
        for rate in (0, -1, math.nan, math.inf, -math.inf, True, "100"):
            with self.subTest(rate=rate):
                report = _chart_report()
                report["results"][0]["requests_per_second"] = rate
                with self.assertRaisesRegex(ValueError, "finite and greater"):
                    render_throughput_svg(report, 3)

    def test_chart_escapes_labels_and_environment(self) -> None:
        """
        Verify that SVG labels and environment values remain escaped text.

        Returns
        -------
        None
            This test does not return a value.
        """
        report = _chart_report()
        label = 'Framework <preview> & "quoted"'
        report["settings"]["frameworks"][0] = label
        report["results"][0]["framework"] = label
        report["environment"]["python"] = "3.14.8 <preview> & build"
        root = ElementTree.fromstring(render_throughput_svg(report, 3))
        text = "".join(root.itertext())
        self.assertIn(label, text)
        self.assertIn("Python 3.14.8 <preview> & build", text)
        self.assertEqual(root.findall(".//preview"), [])

class TestComparisonReports(unittest.TestCase):
    """Verify that every artifact publishes the same comparative results."""

    def test_artifacts_preserve_valid_data_and_label_failures(self) -> None:
        """
        Verify consistent report artifacts and explicit failure placeholders.

        Returns
        -------
        None
            This test does not return a value.
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
