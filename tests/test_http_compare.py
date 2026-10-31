import csv
import json
import math
import os
import socket
import unittest
from argparse import Namespace
from contextlib import chdir, closing, redirect_stderr, redirect_stdout
from importlib import import_module
from importlib.util import find_spec
from inspect import iscoroutinefunction
from io import StringIO, TextIOWrapper
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, TypedDict, Unpack
from unittest.mock import Mock, call, patch
from urllib.parse import urlsplit
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
        Fixture counts and timings with an intentionally inflated client rate.
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
        Normalized samples that distinguish medians from pooled statistics.
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

def _probe_connection() -> Mock:
    """
    Build a connection double with two persistent Hello World responses.

    Returns
    -------
    Mock
        Connection yielding two successful HTTP/1.1 text responses.
    """
    responses = []
    for _ in range(2):
        response = Mock(status=200, version=11, will_close=False)
        response.read.return_value = b"Hello World"
        response.getheader.return_value = "text/plain; charset=utf-8"
        responses.append(response)
    connection = Mock()
    connection.getresponse.side_effect = responses
    return connection

def _startup_log(
    directory: Path, pids: list[int], *,
    server: str = "granian", started: bool = True,
) -> Path:
    """
    Write fixture startup events for the selected server.

    Parameters
    ----------
    directory : Path
        Directory containing the generated server log.
    pids : list[int]
        Worker process identifiers to include in the log.
    server : str, optional
        Server whose native log format to use; default is ``granian``.
    started : bool, optional
        Include completed application startup events when true.

    Returns
    -------
    Path
        Path to the generated UTF-8 server log.
    """
    events = []
    for index, pid in enumerate(pids, 1):
        if server == "uvicorn":
            events.append(f"INFO:     Started server process [{pid}]\n")
            if started:
                events.append("INFO:     Application startup complete.\n")
        else:
            events.append(f"[INFO] Spawning worker-{index} with PID: {pid}\n")
            if started:
                events.append(f"[INFO] Started worker-{index}\n")
    path = directory / "server.log"
    path.write_text("".join(events), encoding="utf-8")
    return path

def _chart_report() -> dict[str, Any]:
    """
    Build a synthetic five-framework throughput comparison.

    Returns
    -------
    dict[str, Any]
        Complete report using fixture rates rather than measured performance.
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
            "warmup_frameworks": ["orionis-rsgi", "orionis-asgi"],
            "repetitions": 3, "duration_seconds": 10,
        },
        "environment": {
            "python": "3.14.8", "commit": "abc123456",
            "recorded_at": "2026-10-15T16:00:00+00:00",
            "versions": {"granian": "2.8.4", "uvicorn": "0.54.0"},
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
            Check successful request counts, errors, throughput, and latency units.
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
            Confirm that invalid rate denominators and success counts are rejected.
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
            Check numeric validation across counts, durations, and percentiles.
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
            Confirm independent sample medians and accumulated request totals.
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
            Confirm that failed samples suppress comparative metrics.
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
            Confirm that an empty sample sequence cannot produce a result.
        """
        # An empty run must fail rather than publish a success-shaped result.
        with self.assertRaises(ValueError):
            aggregate_samples([])

class TestOrionisApplication(unittest.TestCase):
    """Verify the Orionis factory contains only native app configuration."""

    def test_factory_uses_staged_routes_without_tracking(self) -> None:
        """
        Verify native app creation uses staged routes without startup hooks.

        Returns
        -------
        None
            Check app configuration and the absence of copied files or callbacks.
        """
        app = Mock()
        app.withRouting.return_value = app
        app.withConfigApp.return_value = app
        app.create.return_value = app
        with (
            TemporaryDirectory() as temporary,
            chdir(temporary),
            patch.object(
                orionis_benchmark, "Application", return_value=app,
            ) as application,
        ):
            result = orionis_benchmark.create_application()
            directory = Path.cwd()
            self.assertTrue(directory.samefile(temporary))
            self.assertEqual(list(directory.iterdir()), [])
            application.assert_called_once_with(base_path=directory)
            app.withRouting.assert_called_once_with(api="_http_compare_routes.py")
            app.withConfigApp.assert_called_once_with(
                env="production", debug=False, maintenance=False,
            )
            app.on.assert_not_called()
            app.create.assert_called_once_with()
            self.assertIs(result, app)

@unittest.skipUnless(
    all(
        find_spec(name) is not None
        for name in ("fastapi", "litestar", "starlette", "uvicorn")
    ),
    "Install the benchmark dependency group to test the real applications",
)
class TestMinimalApplications(unittest.TestCase):
    """Verify the five native servers without publishing performance results."""

    def test_native_asgi_routers_have_only_the_root_route(self) -> None:
        """
        Verify native ASGI routers register only the measured root route.

        Returns
        -------
        None
            Check async handlers and the absence of auxiliary routes.
        """
        from benchmarks.http_compare.apps import fastapi, litestar, starlette

        for module in (fastapi, litestar, starlette):
            with self.subTest(framework=module.__name__):
                self.assertTrue(iscoroutinefunction(module.hello))
                app = module.create_application()
                self.assertEqual([route.path for route in app.routes], ["/"])

    def test_native_apps_serve_only_hello_world(self) -> None:
        """
        Verify payload, keep-alive, route isolation, and native server cleanup.

        Returns
        -------
        None
            Check real responses, framework preparation, and server termination.
        """
        sample = _successful_runs()[0]

        def load(
            _oha: Path,
            url: str,
            _seconds: float,
            _connections: int,
            _output: Path,
            _commands: list[dict[str, Any]],
        ) -> dict[str, int | float]:
            """
            Send correctness requests instead of generating benchmark load.

            Parameters
            ----------
            _oha : Path
                Load-generator path, unused by this double.
            url : str
                Root URL of the running benchmark application.
            _seconds : float
                Requested duration, unused by this double.
            _connections : int
                Requested concurrency, unused by this double.
            _output : Path
                Measurement output path, unused by this double.
            _commands : list[dict[str, Any]]
                Command log, unused by this double.

            Returns
            -------
            dict[str, int | float]
                Successful fixture sample after validating HTTP responses.
            """
            with closing(compare_run.http.client.HTTPConnection(
                urlsplit(url).netloc, timeout=5,
            )) as connection:
                for _ in range(2):
                    connection.request("GET", "/")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b"Hello World")
                    self.assertEqual(
                        response.getheader("content-type", "").split(";", 1)[0],
                        "text/plain",
                    )
                    self.assertEqual(response.version, 11)
                    self.assertFalse(response.will_close)
                for path in ("/_benchmark/worker", "/docs", "/openapi.json"):
                    connection.request("GET", path)
                    response = connection.getresponse()
                    self.assertEqual(response.status, 404, path)
                    response.read()
            return sample

        args = Namespace(warmup=0.1, duration=0.1, connections=1, repetitions=1)
        cases = [
            (framework, workers)
            for framework in compare_run.FRAMEWORKS.values()
            for workers in (1, 2)
            if workers == 1 or (
                framework.server == "uvicorn" and compare_run.sys.platform != "win32"
            )
        ]
        for framework, workers in cases:
            with (
                self.subTest(framework=framework.name, workers=workers),
                TemporaryDirectory() as temporary,
            ):
                output = Path(temporary)
                (output / "logs").mkdir()
                (output / "raw").mkdir()
                row = {"status": "pending"}
                with (
                    patch.object(compare_run, "run_load", side_effect=load) as generate,
                    patch.object(
                        compare_run, "stop_server", wraps=compare_run.stop_server,
                    ) as stop,
                ):
                    compare_run.benchmark_case(
                        framework, workers, args, output / "unused-oha",
                        output, [], row,
                    )
                self.assertEqual(row["status"], "ok")
                self.assertEqual("warmup" in row, framework.requires_warmup)
                self.assertEqual(generate.call_count, 1 + framework.requires_warmup)
                self.assertIsNotNone(stop.call_args.args[0].poll())

class _LoadOptions(TypedDict):
    """Describe the subprocess options used by the load runner."""

    stdout: TextIOWrapper
    stderr: TextIOWrapper
    timeout: float
    check: bool
    creationflags: int

class TestLoadGenerator(unittest.TestCase):
    """Verify measurements and raw evidence survive subprocess failures."""

    def test_load_preserves_output_and_measurement_shape(self) -> None:
        """
        Verify successful load retains both streams and normalized metrics.

        Returns
        -------
        None
            Check output files, command records, timeout, and parsed measurements.
        """
        raw = json.dumps(_measurement())
        diagnostic = "load diagnostic\n"
        script = (
            f"import sys; sys.stdout.write({raw!r}); "
            f"sys.stderr.write({diagnostic!r})"
        )
        execute = compare_run.subprocess.run

        def run(
            _command: list[str], **kwargs: Unpack[_LoadOptions],
        ) -> compare_run.subprocess.CompletedProcess[bytes]:
            """
            Run a Python stand-in with the original subprocess options.

            Parameters
            ----------
            _command : list[str]
                Original load command, unused by this double.
            **kwargs : Unpack[_LoadOptions]
                Stream, timeout, and execution options to forward.

            Returns
            -------
            CompletedProcess[bytes]
                Result of the stand-in process that emits fixture measurements.
            """
            return execute([compare_run.sys.executable, "-B", "-c", script], **kwargs)

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "load.json"
            commands = []
            with patch.object(compare_run.subprocess, "run", side_effect=run) as load:
                measured = compare_run.run_load(
                    Path("oha"), "http://127.0.0.1:8000/", 1, 10, output, commands,
                )
            self.assertEqual(measured, parse_measurement(json.loads(raw)))
            self.assertEqual(output.read_text(encoding="utf-8"), raw)
            self.assertEqual(
                output.with_suffix(".stderr.log").read_text(encoding="utf-8"),
                diagnostic,
            )
            self.assertEqual(commands, [{
                "kind": "oha", "argv": load.call_args.args[0], "output": str(output),
            }])
            self.assertEqual(load.call_args.kwargs["timeout"], 31)

    def test_load_preserves_output_on_process_failure(self) -> None:
        """
        Verify failed load retains diagnostics without parsing partial output.

        Returns
        -------
        None
            Check the native exit code and retained stdout and stderr.
        """
        execute = compare_run.subprocess.run

        def run(
            _command: list[str], **kwargs: Unpack[_LoadOptions],
        ) -> compare_run.subprocess.CompletedProcess[bytes]:
            """
            Emit partial output and fail through a real subprocess.

            Parameters
            ----------
            _command : list[str]
                Original load command, unused by this double.
            **kwargs : Unpack[_LoadOptions]
                Stream, timeout, and execution options to forward.

            Returns
            -------
            CompletedProcess[bytes]
                Result when the caller permits a nonzero exit code.

            Raises
            ------
            CalledProcessError
                If the forwarded options require a successful exit.
            """
            return execute([
                compare_run.sys.executable, "-B", "-c",
                (
                    "import sys; sys.stdout.write('{'); "
                    "sys.stderr.write('load failed'); sys.exit(7)"
                ),
            ], **kwargs)

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "load.json"
            with (
                patch.object(compare_run.subprocess, "run", side_effect=run),
                self.assertRaises(compare_run.subprocess.CalledProcessError) as raised,
            ):
                compare_run.run_load(
                    Path("oha"), "http://127.0.0.1:8000/", 1, 10, output, [],
                )
            self.assertEqual(raised.exception.returncode, 7)
            self.assertEqual(output.read_text(encoding="utf-8"), "{")
            self.assertEqual(
                output.with_suffix(".stderr.log").read_text(encoding="utf-8"),
                "load failed",
            )

    def test_load_preserves_output_on_timeout(self) -> None:
        """
        Verify timed-out load retains flushed partial output.

        Returns
        -------
        None
            Check timeout propagation and retained diagnostic streams.
        """
        execute = compare_run.subprocess.run

        def run(
            _command: list[str], **kwargs: Unpack[_LoadOptions],
        ) -> compare_run.subprocess.CompletedProcess[bytes]:
            """
            Run a Python subprocess with a short timeout.

            Parameters
            ----------
            _command : list[str]
                Original load command, unused by this double.
            **kwargs : Unpack[_LoadOptions]
                Execution options whose timeout is reduced for this test.

            Returns
            -------
            CompletedProcess[bytes]
                Process result if execution finishes before the deadline.

            Raises
            ------
            TimeoutExpired
                When the subprocess exceeds the shortened timeout.
            """
            kwargs["timeout"] = 1
            return execute([
                compare_run.sys.executable, "-B", "-c",
                (
                    "import sys, time; sys.stdout.write('{'); sys.stdout.flush(); "
                    "sys.stderr.write('unfinished'); sys.stderr.flush(); time.sleep(10)"
                ),
            ], **kwargs)

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "load.json"
            with (
                patch.object(compare_run.subprocess, "run", side_effect=run),
                self.assertRaises(compare_run.subprocess.TimeoutExpired),
            ):
                compare_run.run_load(
                    Path("oha"), "http://127.0.0.1:8000/", 1, 10, output, [],
                )
            self.assertEqual(output.read_text(encoding="utf-8"), "{")
            self.assertEqual(
                output.with_suffix(".stderr.log").read_text(encoding="utf-8"),
                "unfinished",
            )

class TestBenchmarkRunner(unittest.TestCase):
    """Verify equal server settings, warmup isolation, and worker cleanup."""

    def test_help_omits_internal_options(self) -> None:
        """
        Verify hidden CLI options remain accepted with their defaults.

        Returns
        -------
        None
            Check help output and parsing of the internal warmup option.
        """
        parser = compare_run.build_parser()
        self.assertNotIn("warmup", parser.format_help().lower())
        self.assertEqual(parser.parse_args([]).warmup, 2)
        self.assertEqual(parser.parse_args(["--warmup", "0.5"]).warmup, 0.5)

    def test_frameworks_use_their_assigned_servers(self) -> None:
        """
        Verify native servers and matching settings for every framework.

        Returns
        -------
        None
            Check server assignments, launcher modules, and native CLI arguments.
        """
        servers = {
            "orionis-rsgi": "granian", "orionis-asgi": "granian",
            "fastapi": "uvicorn", "litestar": "uvicorn", "starlette": "uvicorn",
        }
        for framework in compare_run.FRAMEWORKS.values():
            with self.subTest(framework=framework.name):
                server = servers[framework.name]
                command = compare_run.server_command(framework, 2, 8000)
                self.assertEqual(framework.server, server)
                server_module = (
                    "benchmarks.http_compare.uvicorn_server"
                    if server == "uvicorn" else server
                )
                native_options = [
                    "--interface", framework.interface,
                    "--http", "1",
                    "--runtime-threads", "1",
                    "--task-impl", "asyncio",
                    "--http1-keep-alive", "--no-ws", "--no-reload",
                    "--no-respawn-failed-workers", "--no-metrics",
                ] if server == "granian" else [
                    "--http", "h11", "--ws", "none",
                    "--lifespan", "on", "--no-use-colors",
                ]
                self.assertEqual(command, [
                    compare_run.sys.executable, "-B", "-m", server_module,
                    framework.target, "--factory",
                    "--host", "127.0.0.1", "--port", "8000",
                    "--workers", "2", "--loop", "asyncio",
                    "--no-access-log", "--log-level", "info",
                    *native_options,
                ])

    def test_orionis_preparation_uses_only_two_root_requests(self) -> None:
        """
        Verify Orionis preparation sends only two root requests.

        Returns
        -------
        None
            Check worker readiness, persistent requests, and connection cleanup.
        """
        process = Mock()
        process.poll.return_value = None
        for workers in range(1, 5):
            with self.subTest(workers=workers), TemporaryDirectory() as temporary:
                pids = list(range(5678, 5678 + workers))
                log_path = _startup_log(Path(temporary), pids)
                connection = _probe_connection()
                with (
                    patch.object(compare_run, "track_children"),
                    patch.object(compare_run, "check_workers"),
                    patch.object(
                        compare_run.http.client, "HTTPConnection",
                        return_value=connection,
                    ) as connect,
                    patch.object(compare_run.time, "sleep"),
                ):
                    result = compare_run.wait_until_ready(
                        process, 8000, log_path, workers, {},
                        framework=compare_run.FRAMEWORKS["orionis-rsgi"],
                    )

                self.assertEqual(result, set(pids))
                connect.assert_called_once_with("127.0.0.1", 8000, timeout=1)
                self.assertEqual(connection.request.call_args_list, [
                    call("GET", "/"), call("GET", "/"),
                ])
                self.assertEqual(connection.getresponse.call_count, 2)
                connection.close.assert_called_once_with()

    def test_startup_without_warmup_never_sends_http_requests(self) -> None:
        """
        Verify other frameworks become ready without HTTP preparation.

        Returns
        -------
        None
            Confirm readiness uses TCP checks without sending HTTP requests.
        """
        process = Mock()
        process.poll.return_value = None
        for workers in range(1, 5):
            with self.subTest(workers=workers), TemporaryDirectory() as temporary:
                pids = list(range(5678, 5678 + workers))
                log_path = _startup_log(Path(temporary), pids, server="uvicorn")
                with (
                    patch.object(compare_run, "track_children"),
                    patch.object(compare_run, "check_workers") as check,
                    patch.object(
                        compare_run.http.client, "HTTPConnection",
                    ) as connect,
                    patch.object(
                        compare_run.socket, "create_connection",
                    ) as tcp,
                ):
                    result = compare_run.wait_until_ready(
                        process, 8000, log_path, workers, {},
                        framework=compare_run.FRAMEWORKS["fastapi"],
                    )

                self.assertEqual(result, set(pids))
                self.assertEqual(check.call_args_list, [
                    call(process, set(pids), {}), call(process, set(pids), {}),
                ])
                tcp.assert_called_once_with(("127.0.0.1", 8000), timeout=1)
                tcp.return_value.close.assert_called_once_with()
                connect.assert_not_called()

    def test_startup_without_warmup_still_waits_for_workers(self) -> None:
        """
        Verify skipping warmup does not bypass worker startup checks.

        Returns
        -------
        None
            Confirm incomplete worker startup blocks measurements until timeout.
        """
        process = Mock()
        process.poll.return_value = None
        with TemporaryDirectory() as temporary:
            log_path = _startup_log(Path(temporary), [5678], server="uvicorn")
            with (
                patch.object(compare_run, "track_children"),
                patch.object(compare_run, "check_workers") as check,
                patch.object(compare_run.http.client, "HTTPConnection") as connect,
                patch.object(compare_run.socket, "create_connection") as tcp,
                patch.object(compare_run.time, "sleep") as pause,
                patch.object(
                    compare_run.time, "monotonic", side_effect=[0, 0, 61],
                ),
                self.assertRaisesRegex(TimeoutError, "2 ready workers"),
            ):
                compare_run.wait_until_ready(
                    process, 8000, log_path, 2, {},
                    framework=compare_run.FRAMEWORKS["fastapi"],
                )

        check.assert_not_called()
        connect.assert_not_called()
        tcp.assert_not_called()
        pause.assert_called_once_with(0.1)

    def test_unstarted_worker_times_out_before_measurements(self) -> None:
        """
        Verify spawned workers require completed application startup.

        Returns
        -------
        None
            Confirm incomplete startup times out without opening HTTP connections.
        """
        process = Mock()
        process.poll.return_value = None
        with TemporaryDirectory() as temporary:
            log_path = _startup_log(
                Path(temporary), [5678, 5679], started=False,
            )
            with (
                patch.object(compare_run, "track_children"),
                patch.object(compare_run, "check_workers"),
                patch.object(
                    compare_run.http.client, "HTTPConnection",
                ) as connect,
                patch.object(compare_run.time, "sleep"),
                patch.object(
                    compare_run.time, "monotonic", side_effect=[0, 0, 61],
                ),
                self.assertRaisesRegex(TimeoutError, "2 ready workers"),
            ):
                compare_run.wait_until_ready(
                    process, 8000, log_path, 2, {},
                    framework=compare_run.FRAMEWORKS["orionis-rsgi"],
                )

        connect.assert_not_called()

    def test_uvicorn_waits_for_every_application_startup(self) -> None:
        """
        Verify Uvicorn waits for every worker's application startup.

        Returns
        -------
        None
            Check that partial startup logs cannot admit a ready server.
        """
        process = Mock()
        process.poll.return_value = None
        for completed in (0, 1):
            with self.subTest(completed=completed), TemporaryDirectory() as temporary:
                log_path = _startup_log(
                    Path(temporary), [5678, 5679], server="uvicorn", started=False,
                )
                with log_path.open("a", encoding="utf-8") as log:
                    log.write("INFO:     Application startup complete.\n" * completed)
                with (
                    patch.object(compare_run, "track_children"),
                    patch.object(compare_run, "check_workers") as check,
                    patch.object(compare_run.socket, "create_connection") as tcp,
                    patch.object(compare_run.time, "sleep"),
                    patch.object(
                        compare_run.time, "monotonic", side_effect=[0, 0, 61],
                    ),
                    self.assertRaisesRegex(TimeoutError, "Uvicorn.*2 ready workers"),
                ):
                    compare_run.wait_until_ready(
                        process, 8000, log_path, 2, {},
                        framework=compare_run.FRAMEWORKS["fastapi"],
                    )
                check.assert_not_called()
                tcp.assert_not_called()

    def test_readiness_rejects_an_unowned_native_worker(self) -> None:
        """
        Verify readiness rejects worker processes without ownership.

        Returns
        -------
        None
            Confirm foreign worker identifiers block HTTP preparation.
        """
        process = Mock()
        process.poll.return_value = None
        with TemporaryDirectory() as temporary:
            log_path = _startup_log(Path(temporary), [9999])
            with (
                patch.object(compare_run, "track_children"),
                patch.object(
                    compare_run.http.client, "HTTPConnection",
                ) as connect,
                self.assertRaisesRegex(RuntimeError, "9999"),
            ):
                compare_run.wait_until_ready(
                    process, 8000, log_path, 1, {},
                    framework=compare_run.FRAMEWORKS["orionis-rsgi"],
                )

        connect.assert_not_called()

    def test_preparation_rejects_invalid_http_responses(self) -> None:
        """
        Verify probe status, payload, media type, and keep-alive checks.

        Returns
        -------
        None
            Confirm invalid payloads, statuses, media types, or keep-alive fail.
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
                    compare_run._probe_response(connection)
                response.read.assert_called_once_with()

    def test_failed_preparation_never_starts_load(self) -> None:
        """
        Verify that failed preparation prevents load and cleans up the server.

        Returns
        -------
        None
            Check that preparation failure blocks load and stops the server.
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
                    side_effect=TimeoutError("server not ready"),
                ),
                patch.object(compare_run, "run_load") as load,
                patch.object(compare_run, "stop_server") as stop,
                self.assertRaisesRegex(TimeoutError, "server not ready"),
            ):
                compare_run.benchmark_case(
                    compare_run.FRAMEWORKS["orionis-rsgi"], 2, args,
                    output / "oha", output, [], row,
                )

        load.assert_not_called()
        stop.assert_called_once_with(process, {})
        self.assertNotIn("warmup", row)
        self.assertNotIn("samples", row)

    def test_other_frameworks_start_measurements_without_warmup(self) -> None:
        """
        Verify other frameworks run only the requested measurement load.

        Returns
        -------
        None
            Check measured runs, environment isolation, and cleanup without warmup.
        """
        args = Namespace(warmup=2, duration=10, connections=100, repetitions=3)
        sample = _successful_runs()[0]
        for name in ("fastapi", "litestar", "starlette"):
            with self.subTest(framework=name), TemporaryDirectory() as temporary:
                process = Mock()
                row = {"status": "pending"}
                output = Path(temporary)
                (output / "logs").mkdir()
                (output / "raw").mkdir()
                with (
                    patch.dict(os.environ, {
                        "GRANIAN_PORT": "9000", "UVICORN_PORT": "9001",
                    }),
                    patch.object(
                        compare_run.subprocess, "Popen", return_value=process,
                    ) as start,
                    patch.object(compare_run, "wait_until_ready") as prepare,
                    patch.object(compare_run, "check_workers") as check,
                    patch.object(compare_run, "stop_server") as stop,
                    patch.object(
                        compare_run, "run_load", return_value=sample,
                    ) as load,
                ):
                    compare_run.benchmark_case(
                        compare_run.FRAMEWORKS[name], 1, args,
                        output / "oha", output, [], row,
                    )

                self.assertEqual(
                    [entry.args[2] for entry in load.call_args_list],
                    [10, 10, 10],
                )
                self.assertEqual(
                    prepare.call_args.kwargs["framework"], compare_run.FRAMEWORKS[name],
                )
                self.assertFalse(any(
                    key.startswith(("GRANIAN_", "UVICORN_"))
                    for key in start.call_args.kwargs["env"]
                ))
                self.assertNotIn("warmup", row)
                self.assertEqual(row["status"], "ok")
                self.assertEqual(row["samples"], [sample] * args.repetitions)
                self.assertEqual(check.call_count, args.repetitions)
                stop.assert_called_once_with(process, {})

    def test_warmup_is_retained_but_excluded_from_measured_results(self) -> None:
        """
        Verify that retained warmup samples never affect measured results.

        Returns
        -------
        None
            Confirm warmup precedes measured runs without affecting their metrics.
        """
        self.assertEqual(compare_run.build_parser().parse_args([]).warmup, 2)
        # Make warmup much faster than measured runs to expose contamination.
        raw = _measurement()
        raw["statusCodeDistribution"] = {"200": 1000000}
        raw["errorDistribution"] = {}
        raw["summary"]["total"] = 2
        warmup = parse_measurement(raw)
        measured = _successful_runs()
        args = Namespace(warmup=2, duration=10, connections=100, repetitions=3)
        for name in ("orionis-rsgi", "orionis-asgi"):
            with self.subTest(framework=name), TemporaryDirectory() as temporary:
                process = Mock()
                process.poll.return_value = None
                row = {"status": "pending"}
                order = Mock()
                output = Path(temporary)
                (output / "logs").mkdir()
                (output / "raw").mkdir()
                with (
                    patch.object(
                        compare_run.subprocess, "Popen", return_value=process,
                    ),
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
                        compare_run.FRAMEWORKS[name], 1, args,
                        output / "oha", output, [], row,
                    )

                self.assertEqual(
                    prepare.call_args.kwargs["framework"], compare_run.FRAMEWORKS[name],
                )
                self.assertEqual(row["status"], "ok")
                self.assertEqual(row["warmup"]["requests"], 1000000)
                self.assertEqual(row["requests"], 1110)
                self.assertEqual(row["requests_per_second"], 100)
                self.assertEqual(row["samples"], measured)
                self.assertEqual(
                    [entry.args[2] for entry in load.call_args_list],
                    [2, 10, 10, 10],
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
            Check owned worker termination and escalation after supervisor exit.
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

    def test_cleanup_terminates_each_owned_process_once(self) -> None:
        """
        Verify cleanup terminates each owned process only once.

        Returns
        -------
        None
            Check supervisor and worker termination without redundant kills.
        """
        process = Mock(pid=1234)
        parent = Mock(pid=1234)
        worker = Mock(pid=5678)
        with (
            patch.object(compare_run.sys, "platform", "win32"),
            patch.object(compare_run, "track_children"),
            patch.object(compare_run.psutil, "Process", return_value=parent),
            patch.object(compare_run.psutil, "wait_procs", return_value=([], [])),
        ):
            compare_run.stop_server(process, {worker.pid: worker})

        parent.terminate.assert_called_once_with()
        worker.terminate.assert_called_once_with()
        parent.kill.assert_not_called()
        worker.kill.assert_not_called()
        process.wait.assert_called_once_with(timeout=5)

    def test_native_workers_require_a_living_owned_process(self) -> None:
        """
        Verify dead, foreign, and zombie workers fail health checks.

        Returns
        -------
        None
            Confirm only living owned workers satisfy native readiness checks.
        """
        for scenario, pid in (
            ("dead", 5678), ("foreign", 9999), ("zombie", 5678),
        ):
            with self.subTest(scenario=scenario):
                process = Mock(pid=1234)
                process.poll.return_value = None
                worker = Mock(pid=5678)
                worker.is_running.return_value = scenario != "dead"
                worker.status.return_value = (
                    compare_run.psutil.STATUS_ZOMBIE if scenario == "zombie"
                    else compare_run.psutil.STATUS_RUNNING
                )
                parent = Mock()
                parent.children.return_value = [worker]
                with (
                    patch.object(compare_run.psutil, "Process", return_value=parent),
                    self.assertRaisesRegex(RuntimeError, str(pid)),
                ):
                    compare_run.check_workers(process, {pid}, {})

    def test_uvicorn_single_worker_is_the_server_process(self) -> None:
        """
        Verify Uvicorn's main process counts as a living single worker.

        Returns
        -------
        None
            Check main-process ownership and rejection of dead or zombie states.
        """
        for status in ("running", "dead", "zombie"):
            with self.subTest(status=status):
                process = Mock(pid=1234)
                process.poll.return_value = None
                owner = Mock(pid=1234)
                owner.children.return_value = []
                owner.is_running.return_value = status != "dead"
                owner.status.return_value = (
                    compare_run.psutil.STATUS_ZOMBIE if status == "zombie"
                    else compare_run.psutil.STATUS_RUNNING
                )
                with patch.object(
                    compare_run.psutil, "Process", return_value=owner,
                ):
                    if status == "running":
                        compare_run.check_workers(process, {1234}, {})
                    else:
                        with self.assertRaisesRegex(RuntimeError, "1234"):
                            compare_run.check_workers(process, {1234}, {})

    def test_main_preserves_partial_samples_and_continues(self) -> None:
        """
        Verify that partial failures retain samples and allow later cases.

        Returns
        -------
        None
            Check partial diagnostics, continued execution, and failure labeling.
        """
        # Keep actual CLI orchestration and artifact persistence under test.
        samples = _successful_runs()
        environment = {
            "os": "CI test host", "python": "3.14.8",
            "versions": {"granian": "2.8.4", "uvicorn": "0.54.0"},
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
                Framework selecting a failed or successful fixture result.
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
                Store complete aggregate metrics or a partial failed sample.

            Raises
            ------
            RuntimeError
                When FastAPI is selected, after recording the first sample.
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
            diagnostics = json.loads(
                (output / "diagnostics.json").read_text(encoding="utf-8"),
            )
            markdown = (output / "summary.md").read_text(encoding="utf-8")
            charts = list(output.glob("throughput-*.svg"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(charts, [])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(diagnostics["settings"]["warmup_frameworks"], [])
        failed, successful = saved["results"]
        self.assertEqual(failed["framework"], "fastapi")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(diagnostics["results"][0]["samples"], [samples[0]])
        self.assertIn("worker exited", diagnostics["results"][0]["reason"])
        self.assertNotIn("samples", failed)
        self.assertNotIn("reason", failed)
        for metric in METRICS:
            self.assertNotIn(metric, failed)
        self.assertEqual(successful["framework"], "starlette")
        self.assertEqual(successful["status"], "ok")
        self.assertEqual(successful["requests_per_second"], 100)
        self.assertIn("| fastapi | asgi | 1 | failed | - | - | - | - | - |", markdown)
        self.assertIn("| starlette | asgi | 1 | ok | 100.00 |", markdown)

    def test_main_keeps_failure_reports_for_all_exit_paths(self) -> None:
        """
        Verify failed exit paths retain diagnostic reports.

        Returns
        -------
        None
            Check setup failures, interruptions, unsupported cases, and chart gates.
        """
        failure_message = "Warmup failed during preparation"
        for scenario, setup_error, benchmark_error in (
            ("setup", RuntimeError(failure_message), None),
            ("setup-empty", RuntimeError(""), None),
            ("case", None, RuntimeError(failure_message)),
            ("interrupt", None, KeyboardInterrupt),
            ("unsupported", None, None),
        ):
            with self.subTest(scenario=scenario), TemporaryDirectory() as temporary:
                output = Path(temporary) / "results"
                with (
                    patch.object(compare_run.sys, "platform", "win32"),
                    patch.object(
                        compare_run, "collect_environment",
                        return_value=_chart_report()["environment"],
                    ),
                    patch.object(
                        compare_run, "resolve_oha",
                        return_value=Path(temporary) / "oha",
                        side_effect=setup_error,
                    ),
                    patch.object(
                        compare_run, "benchmark_case",
                        side_effect=benchmark_error,
                    ) as benchmark,
                    patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}),
                    redirect_stdout(StringIO()) as stdout,
                    redirect_stderr(StringIO()) as stderr,
                ):
                    exit_code = compare_run.main([
                        "--workers", "2" if scenario == "unsupported" else "1",
                        "--frameworks",
                        "orionis-asgi" if scenario == "unsupported" else "fastapi",
                        "--output-dir", str(output),
                    ])
                report = json.loads(
                    (output / "summary.json").read_text(encoding="utf-8"),
                )
                diagnostics = json.loads(
                    (output / "diagnostics.json").read_text(encoding="utf-8"),
                )
                self.assertEqual(exit_code, 1)
                self.assertEqual(list(output.glob("throughput-*.svg")), [])
                self.assertTrue((output / "commands.json").is_file())
                public_output = stdout.getvalue() + stderr.getvalue()
                self.assertNotIn("warmup", public_output.lower())
                self.assertNotIn("preparation", public_output.lower())
                if scenario.startswith("setup") or scenario == "case":
                    self.assertIn("diagnostics.json", stderr.getvalue())
                if scenario.startswith("setup"):
                    benchmark.assert_not_called()
                    self.assertEqual(diagnostics["error"], str(setup_error))
                    self.assertIn("diagnostics.json", report["error"])
                    self.assertEqual(report["results"], [])
                else:
                    row = report["results"][0]
                    expected = "unsupported" if scenario == "unsupported" else "failed"
                    self.assertEqual(row["status"], expected)
                    for metric in METRICS:
                        self.assertNotIn(metric, row)
                    if scenario == "unsupported":
                        benchmark.assert_not_called()
                    else:
                        self.assertEqual(
                            diagnostics["results"][0]["reason"],
                            failure_message if scenario == "case"
                            else "Interrupted by user",
                        )

    def test_windows_preserves_single_worker_comparisons(self) -> None:
        """
        Verify Windows rejects unsupported multi-worker comparisons.

        Returns
        -------
        None
            Confirm unsupported cases skip execution and publish no metrics.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            with (
                patch.object(compare_run.sys, "platform", "win32"),
                patch.object(
                    compare_run, "collect_environment",
                    return_value=_chart_report()["environment"],
                ),
                patch.object(
                    compare_run, "resolve_oha", return_value=Path(temporary) / "oha",
                ),
                patch.object(
                    compare_run, "benchmark_case",
                ) as benchmark,
                patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}),
                redirect_stdout(StringIO()),
            ):
                exit_code = compare_run.main([
                    "--workers", "2", "3", "4",
                    "--frameworks", *compare_run.FRAMEWORKS,
                    "--output-dir", str(output),
                ])
            report = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 1)
        benchmark.assert_not_called()
        self.assertEqual(len(report["results"]), 15)
        self.assertTrue(all(
            row["status"] == "unsupported" for row in report["results"]
        ))

    def test_main_validates_only_selected_server_versions(self) -> None:
        """
        Verify version checks require only the selected server.

        Returns
        -------
        None
            Check setup failures and independence from unused server dependencies.
        """
        for name, selected, unused in (
            ("orionis-asgi", "granian", "uvicorn"),
            ("fastapi", "uvicorn", "granian"),
        ):
            for missing in (selected, unused):
                with (
                    self.subTest(framework=name, missing=missing),
                    TemporaryDirectory() as temporary,
                ):
                    output = Path(temporary) / "results"
                    environment = _chart_report()["environment"]
                    environment["versions"][missing] = "not installed"
                    with (
                        patch.object(
                            compare_run, "collect_environment",
                            return_value=environment,
                        ),
                        patch.object(
                            compare_run, "resolve_oha",
                            return_value=Path(temporary) / "oha",
                        ),
                        patch.object(
                            compare_run, "benchmark_case",
                            side_effect=lambda *args: args[-1].update(
                                aggregate_samples(_successful_runs()),
                            ),
                        ) as benchmark,
                        patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}),
                        redirect_stdout(StringIO()),
                        redirect_stderr(StringIO()),
                    ):
                        exit_code = compare_run.main([
                            "--workers", "1", "--frameworks", name,
                            "--output-dir", str(output),
                        ])
                    diagnostics = json.loads(
                        (output / "diagnostics.json").read_text(encoding="utf-8"),
                    )
                    self.assertEqual(exit_code, int(missing == selected))
                    if missing == selected:
                        benchmark.assert_not_called()
                        self.assertIn(
                            f"{selected.capitalize()} "
                            f"{compare_run.SERVER_VERSIONS[selected]} required",
                            diagnostics["error"],
                        )
                    else:
                        benchmark.assert_called_once()

    def test_successful_main_writes_chart_from_saved_report(self) -> None:
        """
        Verify that a successful run saves charts matching its saved report.

        Returns
        -------
        None
            Check saved settings and charts against the published result data.
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
                    "--frameworks", "orionis-rsgi", "orionis-asgi",
                    "fastapi", "litestar", "starlette",
                    "--output-dir", str(output),
                ])
            saved = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            diagnostics = json.loads(
                (output / "diagnostics.json").read_text(encoding="utf-8"),
            )
            charts = {
                path.name: path.read_text(encoding="utf-8")
                for path in output.glob("throughput-*.svg")
            }

        self.assertEqual(exit_code, 0)
        self.assertEqual(saved["schema_version"], 2)
        self.assertEqual(set(saved["settings"]), {"frameworks", "workers"})
        self.assertEqual(diagnostics["settings"]["warmup_seconds"], 2)
        self.assertEqual(
            diagnostics["settings"]["readiness"], "native-server-workers-and-tcp",
        )
        self.assertTrue(diagnostics["settings"]["uvicorn_multi_worker_tcp_nodelay"])
        self.assertEqual(
            diagnostics["settings"]["servers"],
            {
                "orionis-rsgi": "granian", "orionis-asgi": "granian",
                "fastapi": "uvicorn", "litestar": "uvicorn", "starlette": "uvicorn",
            },
        )
        self.assertEqual(
            diagnostics["settings"]["warmup_frameworks"],
            ["orionis-rsgi", "orionis-asgi"],
        )
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
        Verify SVG ranking, scaling, worker filtering, and numeric results.

        Returns
        -------
        None
            Check ranking, bar dimensions, labels, accessibility, and worker filters.
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
        self.assertIn("Successful HTTP 200 requests per second.", svg)
        self.assertIn(">32,000</text>", svg)
        for detail in ("warmup", "connections", "Python", "Granian", "2026-10-15"):
            self.assertNotIn(detail, svg)
        self.assertNotIn("999,999", svg)

    def test_chart_requires_only_result_groups_and_quantities(self) -> None:
        """
        Verify public results reproduce charts without runtime metadata.

        Returns
        -------
        None
            Confirm chart rendering depends only on result groups and quantities.
        """
        report = _chart_report()
        report["settings"] = {"frameworks": report["settings"]["frameworks"]}
        report.pop("environment")
        svg = render_throughput_svg(report, 3)
        self.assertIn("29,800.00", svg)

    def test_chart_rejects_incomplete_failed_or_errored_results(self) -> None:
        """
        Verify that charts reject incomplete or failed comparison data.

        Returns
        -------
        None
            Confirm incomplete, duplicated, or failed comparisons cannot form charts.
        """
        for scenario in (
            "missing", "duplicate", "failed", "errors", "setup", "empty-setup",
        ):
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
                    report["error"] = (
                        "" if scenario == "empty-setup" else "Setup failed"
                    )
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
            Check rejection of invalid throughput values.
        """
        for rate in (0, -1, math.nan, math.inf, -math.inf, True, "100"):
            with self.subTest(rate=rate):
                report = _chart_report()
                report["results"][0]["requests_per_second"] = rate
                with self.assertRaisesRegex(ValueError, "finite and greater"):
                    render_throughput_svg(report, 3)

    def test_chart_escapes_labels_and_omits_environment(self) -> None:
        """
        Verify labels remain escaped text without exposing environment details.

        Returns
        -------
        None
            Check XML-safe labels and omission of environment details.
        """
        report = _chart_report()
        label = 'Framework <preview> & "quoted"'
        report["settings"]["frameworks"][0] = label
        report["results"][0]["framework"] = label
        report["environment"]["python"] = "3.14.8 <preview> & build"
        root = ElementTree.fromstring(render_throughput_svg(report, 3))
        text = "".join(root.itertext())
        self.assertIn(label, text)
        self.assertNotIn("Python 3.14.8 <preview> & build", text)
        self.assertEqual(root.findall(".//preview"), [])

class TestComparisonReports(unittest.TestCase):
    """Verify that every artifact publishes the same comparative results."""

    def test_public_reports_omit_preparation_details(self) -> None:
        """
        Verify public formats omit warmup and unmeasured request counts.

        Returns
        -------
        None
            Check consistent omission across Markdown, JSON, CSV, and SVG.
        """
        report = _chart_report()
        orionis = next(
            row for row in report["results"] if row["framework"] == "orionis-asgi"
        )
        orionis["warmup"] = {**_successful_runs()[0], "requests": 1000000}
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            markdown = write_reports(output, report)
            rendered = {
                "Markdown": markdown,
                "JSON": (output / "summary.json").read_text(encoding="utf-8"),
                "CSV": (output / "summary.csv").read_text(encoding="utf-8"),
                "SVG": render_throughput_svg(report, 3),
            }

        for name, text in rendered.items():
            with self.subTest(format=name):
                self.assertNotIn("warmup", text.lower())
                self.assertNotIn("1000000", text)

    def test_artifacts_preserve_valid_data_and_label_failures(self) -> None:
        """
        Verify consistent report artifacts and explicit failure placeholders.

        Returns
        -------
        None
            Check report consistency, diagnostic preservation, and failure labels.
        """
        # Pair a valid row with an errored row to expose invented failure metrics.
        good = {
            "framework": "orionis-asgi", "interface": "asgi", "workers": 1,
            "warmup": {**_successful_runs()[0], "requests": 1000000},
            **aggregate_samples(_successful_runs()),
        }
        failed = {
            "framework": "fastapi", "interface": "asgi", "workers": 2,
            **aggregate_samples([parse_measurement(_measurement())]),
        }
        report = {
            "settings": {
                "frameworks": ["orionis-asgi", "fastapi"], "workers": [1, 2],
                "connections": 100, "warmup_seconds": 2,
                "warmup_frameworks": ["orionis-asgi"],
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
            diagnostics = json.loads(
                (output / "diagnostics.json").read_text(encoding="utf-8"),
            )
            markdown = (output / "summary.md").read_text(encoding="utf-8")
            with (output / "summary.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))

        self.assertEqual(saved_report, {
            "schema_version": 2,
            "settings": {
                "frameworks": ["orionis-asgi", "fastapi"], "workers": [1, 2],
            },
            "results": [
                {
                    "framework": "orionis-asgi", "interface": "asgi", "workers": 1,
                    "status": "ok", "requests": 1110, "errors": 0,
                    "requests_per_second": 100, "mean_latency_ms": 10,
                    "p50_latency_ms": 5, "p95_latency_ms": 20, "p99_latency_ms": 30,
                },
                {
                    "framework": "fastapi", "interface": "asgi", "workers": 2,
                    "status": "failed", "requests": 100, "errors": 16,
                },
            ],
        })
        self.assertEqual(diagnostics, report)
        self.assertEqual(saved_environment, report["environment"])
        self.assertEqual(markdown, rendered)
        for detail in ("warmup", "## Environment", "CI CPU", "- commit:", "- granian:"):
            self.assertNotIn(detail, markdown)
        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(float(rows[0]["requests_per_second"]), 100)
        self.assertEqual(float(rows[0]["p99_latency_ms"]), 30)
        self.assertEqual(rows[1]["status"], "failed")
        self.assertEqual(rows[1]["errors"], "16")
        self.assertNotIn("reason", rows[1])
        for column in METRICS:
            self.assertEqual(rows[1][column], "")
        self.assertIn(
            "| orionis-asgi | asgi | 1 | ok | 100.00 | 10.00 | "
            "5.00 | 20.00 | 30.00 | 0 |",
            markdown,
        )
        self.assertIn(
            "| fastapi | asgi | 2 | failed | - | - | - | - | - | 16 |",
            markdown,
        )
        self.assertNotIn(failed["reason"], markdown)
        self.assertIn("Comparison failed or incomplete", markdown)

    def test_setup_failure_details_stay_in_diagnostics(self) -> None:
        """
        Verify setup failure details remain confined to diagnostics.

        Returns
        -------
        None
            Check explicit public failure labels without leaking preparation details.
        """
        report = _chart_report()
        report["error"] = "Warmup failed during preparation"
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            markdown = write_reports(output, report)
            public = (output / "summary.json").read_text(encoding="utf-8")
            diagnostics = json.loads(
                (output / "diagnostics.json").read_text(encoding="utf-8"),
            )

        self.assertNotIn("warmup", markdown.lower())
        self.assertNotIn("warmup", public.lower())
        self.assertIn("Comparison failed or incomplete", markdown)
        self.assertIn("diagnostics.json", json.loads(public)["error"])
        self.assertEqual(diagnostics["error"], report["error"])

@unittest.skipUnless(find_spec("uvicorn") is not None, "Install benchmark dependencies")
class TestUvicornTransport(unittest.TestCase):
    """Verify native Uvicorn launching with the multi-worker TCP correction."""

    def test_real_listener_disables_nagle_before_worker_sharing(self) -> None:
        """
        Verify TCP_NODELAY propagates from the listener to accepted sockets.

        Returns
        -------
        None
            Check protocol-zero listeners, inheritable handles, and accepted options.
        """
        from benchmarks.http_compare.uvicorn_server import TcpNoDelayConfig

        config = TcpNoDelayConfig(
            "unused", host="127.0.0.1", port=0, workers=2, log_config=None,
        )
        with closing(config.bind_socket()) as listener:
            self.assertEqual(listener.proto, 0)
            self.assertEqual(
                listener.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 1,
            )
            self.assertEqual(listener.getsockname()[0], "127.0.0.1")
            self.assertTrue(listener.get_inheritable())
            listener.listen(1)
            with (
                closing(socket.create_connection(listener.getsockname(), timeout=5)),
                closing(listener.accept()[0]) as accepted,
            ):
                self.assertEqual(
                    accepted.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 1,
                )

    def test_tcp_option_failure_closes_the_bound_listener(self) -> None:
        """
        Verify TCP configuration failures close the bound listener.

        Returns
        -------
        None
            Check option arguments, error propagation, and socket cleanup.
        """
        from benchmarks.http_compare.uvicorn_server import Config, TcpNoDelayConfig

        listener = Mock(family=socket.AF_INET)
        listener.setsockopt.side_effect = OSError("TCP_NODELAY unavailable")
        config = TcpNoDelayConfig("unused", log_config=None)
        with (
            patch.object(Config, "bind_socket", return_value=listener),
            self.assertRaisesRegex(OSError, "TCP_NODELAY unavailable"),
        ):
            config.bind_socket()
        listener.setsockopt.assert_called_once_with(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1,
        )
        listener.close.assert_called_once_with()

    def test_non_tcp_listener_is_left_unchanged(self) -> None:
        """
        Verify non-TCP listeners remain unchanged.

        Returns
        -------
        None
            Check that no TCP options or premature closure affect the listener.
        """
        from benchmarks.http_compare.uvicorn_server import Config, TcpNoDelayConfig

        listener = Mock(family=socket.AF_UNSPEC)
        config = TcpNoDelayConfig("unused", log_config=None)
        with patch.object(Config, "bind_socket", return_value=listener):
            self.assertIs(config.bind_socket(), listener)
        listener.setsockopt.assert_not_called()
        listener.close.assert_not_called()

    def test_launcher_delegates_to_native_cli_and_restores_config(self) -> None:
        """
        Verify native CLI delegation uses a scoped configuration replacement.

        Returns
        -------
        None
            Check CLI invocation and restoration of the native configuration.
        """
        from benchmarks.http_compare import uvicorn_server

        entrypoint = import_module("uvicorn.main")
        native_config = entrypoint.Config

        def native_main() -> None:
            """
            Check the active Uvicorn configuration.

            Returns
            -------
            None
                Confirm the CLI receives the TCP_NODELAY configuration.
            """
            self.assertIs(entrypoint.Config, uvicorn_server.TcpNoDelayConfig)

        with patch.object(entrypoint, "main", side_effect=native_main) as main:
            uvicorn_server.main()
        main.assert_called_once_with()
        self.assertIs(entrypoint.Config, native_config)

    def test_launcher_preserves_cli_failures_and_exit_codes(self) -> None:
        """
        Verify native CLI failures and exit codes remain unchanged.

        Returns
        -------
        None
            Check exception identity and configuration restoration after failures.
        """
        from benchmarks.http_compare import uvicorn_server

        entrypoint = import_module("uvicorn.main")
        native_config = entrypoint.Config
        for error in (SystemExit(7), RuntimeError("native CLI failed")):
            with self.subTest(error=type(error).__name__):
                with (
                    patch.object(entrypoint, "main", side_effect=error),
                    self.assertRaises(type(error)) as caught,
                ):
                    uvicorn_server.main()
                self.assertIs(caught.exception, error)
                self.assertIs(entrypoint.Config, native_config)
