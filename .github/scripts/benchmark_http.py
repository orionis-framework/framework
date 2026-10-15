import argparse
import hashlib
import http.client
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from contextlib import suppress
from http import HTTPStatus
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import psutil
from summarize_benchmarks import render_report, write_report

# ruff: noqa: T201, S603

OHA_VERSION = "1.16.0"

# Official release binaries: https://github.com/hatoo/oha/releases/tag/v1.16.0
OHA_ASSETS = {
    ("Linux", "amd64"): (
        "oha-linux-amd64",
        "620bb9e16fb53eabc9a3fc45f88bdb41fefa3fee5c05e75892011ce320391716",
    ),
    ("Linux", "arm64"): (
        "oha-linux-arm64",
        "99a790eb8c3e0feaca974bd6b32f0f8d4426a0c5b289f39e833e5b2c7529cd39",
    ),
    ("Darwin", "amd64"): (
        "oha-macos-amd64",
        "5ecbfc5233e3f1d30384e142a9a8dd7ebf9d3298ab22476fabac44a8f2117e08",
    ),
    ("Darwin", "arm64"): (
        "oha-macos-arm64",
        "7dea53ecb8342a7a067e1976fd0aef44ac33d9cc6b1e65c53637ffb932da63c4",
    ),
    ("Windows", "amd64"): (
        "oha-windows-amd64.exe",
        "d692d392e958e7e8e1b16810287e74a835a62255b079ba2766a4b3b04499f267",
    ),
}
WINDOWS_LIMIT = (
    "Granian does not support multiple workers on Windows; "
    "it silently falls back to one worker. This case was not measured."
)

def install_oha(directory: Path) -> Path:
    """
    Download the native oha binary and verify its pinned SHA-256 digest.

    Parameters
    ----------
    directory : Path
        Destination directory for the platform-specific executable.

    Returns
    -------
    Path
        Path to the verified executable with execution permissions enabled.

    Raises
    ------
    KeyError
        If no pinned binary matches the operating system and architecture.
    RuntimeError
        If the downloaded binary does not match its pinned digest.
    """
    # Map platform aliases to the names used by the pinned release assets.
    machine = platform.machine().lower()
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(machine, machine)
    asset, digest = OHA_ASSETS[(platform.system(), architecture)]
    destination = directory / asset
    url = f"https://github.com/hatoo/oha/releases/download/v{OHA_VERSION}/{asset}"
    # Verify the complete download before writing an executable to disk.
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != digest:
        error_msg = f"SHA-256 mismatch for {asset}"
        raise RuntimeError(error_msg)
    destination.write_bytes(data)
    destination.chmod(0o755)
    return destination

def parse_measurement(raw: dict[str, Any]) -> dict[str, int | float]:
    """
    Calculate throughput from successful HTTP 200 responses and elapsed time.

    Parameters
    ----------
    raw : dict[str, Any]
        Decoded oha JSON containing status counts, durations, and latencies.

    Returns
    -------
    dict[str, int | float]
        Successful requests, total errors, elapsed seconds, requests per second,
        and mean and p95 latency in milliseconds.

    Raises
    ------
    ValueError
        If the elapsed time or successful request count is not positive.
    """
    # Keep HTTP and transport errors separate from successful throughput.
    statuses = raw["statusCodeDistribution"]
    successful = statuses.get("200", 0)
    http_errors = sum(count for code, count in statuses.items() if code != "200")
    transport_errors = sum(raw["errorDistribution"].values())
    elapsed = raw["summary"]["total"]
    # Reject runs that cannot establish a successful-request rate.
    if elapsed <= 0 or successful <= 0:
        error_msg = "Load test did not complete any successful requests"
        raise ValueError(error_msg)
    return {
        "requests": successful,
        "errors": http_errors + transport_errors,
        "elapsed_seconds": elapsed,
        "requests_per_second": successful / elapsed,
        "mean_latency_ms": raw["summary"]["average"] * 1000,
        "p95_latency_ms": raw["latencyPercentiles"]["p95"] * 1000,
    }

def run_load(
    oha: Path,
    url: str,
    seconds: float,
    connections: int,
    output: Path,
) -> dict[str, int | float]:
    """
    Run oha and persist its output before parsing successful throughput.

    Parameters
    ----------
    oha : Path
        Verified oha executable.
    url : str
        HTTP endpoint to measure.
    seconds : float
        Load duration in seconds.
    connections : int
        Number of concurrent HTTP/1.1 connections.
    output : Path
        Destination for raw JSON and the sibling standard-error log.

    Returns
    -------
    dict[str, int | float]
        Normalized request counts, errors, throughput, and latency metrics.

    Raises
    ------
    subprocess.CalledProcessError
        If oha exits with a nonzero status.
    subprocess.TimeoutExpired
        If execution exceeds the load duration plus 30 seconds.
    ValueError
        If the output is invalid JSON or contains no successful measurement.
    """
    # Wait for in-flight requests so elapsed time includes their completion.
    command = [
        str(oha),
        "--no-tui",
        "--output-format",
        "json",
        "--http-version",
        "1.1",
        "--wait-ongoing-requests-after-deadline",
        "-t",
        "5s",
        "-c",
        str(connections),
        "-z",
        f"{seconds}s",
        url,
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=seconds + 30,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    # Preserve both streams even when oha reports a failing exit status.
    output.write_text(result.stdout, encoding="utf-8")
    output.with_suffix(".stderr.log").write_text(result.stderr, encoding="utf-8")
    result.check_returncode()
    return parse_measurement(json.loads(result.stdout))

def stop_server(process: subprocess.Popen[bytes]) -> None:
    """
    Terminate the owned server and its workers on every platform.

    Parameters
    ----------
    process : subprocess.Popen[bytes]
        Granian supervisor started without text-mode subprocess streams.

    Returns
    -------
    None
        Wait for the supervisor and captured worker processes to exit.

    Raises
    ------
    RuntimeError
        If workers remain after graceful termination and forced cleanup.
    """
    # Snapshot workers before stopping the supervisor that owns them.
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
    except psutil.NoSuchProcess:
        # Reap a server that exited before its process snapshot was collected.
        process.wait(timeout=5)
        return
    # Stop the supervisor first so it cannot replace workers during cleanup.
    parent.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        # Escalate only after the supervisor's graceful shutdown window expires.
        parent.kill()
        process.wait(timeout=5)
    # Limit cleanup to workers captured from this server's process tree.
    for child in children:
        with suppress(psutil.NoSuchProcess):
            child.terminate()
    # Force termination only for workers that survived the graceful attempt.
    _, alive = psutil.wait_procs(children, timeout=5)
    for child in alive:
        with suppress(psutil.NoSuchProcess):
            child.kill()
    _, survivors = psutil.wait_procs(alive, timeout=5)
    if survivors:
        error_msg = (
            f"Server processes did not exit: {[child.pid for child in survivors]}"
        )
        raise RuntimeError(error_msg)

def wait_until_ready(
    process: subprocess.Popen[bytes],
    port: int,
    directory: Path,
    workers: int,
) -> None:
    """
    Wait for every worker marker and validate the real HTTP response.

    Parameters
    ----------
    process : subprocess.Popen[bytes]
        Granian supervisor whose exit status must remain unset.
    port : int
        Local HTTP port assigned to the benchmark server.
    directory : Path
        Isolated application directory containing worker readiness markers.
    workers : int
        Number of worker factories that must finish initialization.

    Returns
    -------
    None
        Return once all workers are ready and HTTP 200 contains ``Hello World``.

    Raises
    ------
    RuntimeError
        If the server exits or returns an unexpected status or response body.
    TimeoutError
        If all workers are not ready within 60 seconds.
    """
    # A response from one worker does not establish readiness of every worker.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            error_msg = f"Granian exited with code {process.returncode}"
            raise RuntimeError(error_msg)
        # Probe the real endpoint before trusting the worker readiness markers.
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            body = response.read()
            if response.status != HTTPStatus.OK or body != b"Hello World":
                error_msg = (
                    f"Unexpected Hello World response: {response.status}, {body!r}"
                )
                raise RuntimeError(error_msg)
            if len(list((directory / "worker-ready").glob("*"))) == workers:
                return
        except OSError, http.client.HTTPException:
            # Retry transient connection failures while workers finish starting.
            pass
        finally:
            connection.close()
        time.sleep(0.1)
    error_msg = f"Granian did not start all {workers} workers within 60 seconds"
    raise TimeoutError(error_msg)

def benchmark_workers(
    oha: Path,
    workers: int,
    args: argparse.Namespace,
    output: Path,
) -> list[dict[str, int | float]]:
    """
    Run warmup and repeated measurements against an isolated application.

    Parameters
    ----------
    oha : Path
        Verified oha executable.
    workers : int
        Number of Granian worker processes to start.
    args : argparse.Namespace
        Parsed warmup, duration, connection, and repetition settings.
    output : Path
        Existing directory for server logs and raw measurement artifacts.

    Returns
    -------
    list[dict[str, int | float]]
        One normalized measurement per repetition, excluding warmup results.

    Raises
    ------
    RuntimeError
        If warmup reports errors or the server exits during measurement.
    """
    # Keep generated routes and readiness markers outside the repository.
    repo = Path(__file__).resolve().parents[2]
    with TemporaryDirectory(prefix="orionis-http-") as temporary:
        directory = Path(temporary)
        (directory / "routes").mkdir()
        (directory / "worker-ready").mkdir()
        (directory / "routes" / "benchmark.py").write_text(
            "from orionis.support.facades import Route\n"
            "from benchmark_app import hello_world\n"
            "Route.get('/', hello_world).public()\n",
            encoding="utf-8",
        )
        # Ask the operating system for an available local port.
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]
        command = [
            sys.executable,
            "-B",
            "-m",
            "granian",
            "--interface",
            "rsgi",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--http",
            "1",
            "--workers",
            str(workers),
            "--runtime-threads",
            "1",
            "--loop",
            "asyncio",
            "--no-access-log",
            "--no-ws",
            "--log-level",
            "warning",
            "--factory",
            "benchmark_app:create_application",
        ]
        # Expose the isolated application and framework to spawned workers.
        environment = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join(
                [str(Path(__file__).parent.resolve()), str(repo)],
            ),
            # Fixed, public benchmark-only key avoids concurrent .env generation.
            "APP_KEY": "0123456789abcdef0123456789abcdef",
            "APP_ENV": "production",
            "APP_DEBUG": "false",
        }
        # Retain server diagnostics after the temporary application is removed.
        with (output / f"workers-{workers}.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=directory,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32"
                else 0,
            )
            try:
                wait_until_ready(process, port, directory, workers)
                url = f"http://127.0.0.1:{port}/"
                # Exclude warmup from results while requiring an error-free start.
                warmup = run_load(
                    oha,
                    url,
                    args.warmup,
                    args.connections,
                    output / f"workers-{workers}-warmup.json",
                )
                if warmup["errors"]:
                    error_msg = "Warmup returned HTTP or transport errors"
                    raise RuntimeError(error_msg)
                # Measure every repetition against the same initialized workers.
                samples = []
                for repetition in range(1, args.repetitions + 1):
                    sample = run_load(
                        oha,
                        url,
                        args.duration,
                        args.connections,
                        output / f"workers-{workers}-run-{repetition}.json",
                    )
                    samples.append(sample)
                    if process.poll() is not None:
                        error_msg = "Granian exited during measurement"
                        raise RuntimeError(error_msg)
                return samples
            finally:
                # Release the owned process tree on successful and failing runs.
                stop_server(process)

def positive_number(value: str) -> float:
    """
    Parse a finite positive duration from a command-line value.

    Parameters
    ----------
    value : str
        Numeric command-line argument expressed in seconds.

    Returns
    -------
    float
        Finite duration strictly greater than zero.

    Raises
    ------
    ValueError
        If the argument cannot be converted to a float.
    argparse.ArgumentTypeError
        If the converted value is nonpositive, infinite, or NaN.
    """
    # Reject NaN and infinity as well as nonpositive durations.
    number = float(value)
    if not 0 < number < float("inf"):
        error_msg = "must be finite and greater than zero"
        raise argparse.ArgumentTypeError(error_msg)
    return number

def main() -> int:
    """
    Run the worker matrix and preserve partial reports after failures.

    Returns
    -------
    int
        Zero when all supported worker configurations succeed, otherwise one.
    """
    # Validate load settings before creating artifacts or starting subprocesses.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark-results"))
    parser.add_argument(
        "--workers",
        type=int,
        nargs="+",
        choices=range(1, 5),
        default=[1, 2, 3, 4],
    )
    parser.add_argument("--duration", type=positive_number, default=10)
    parser.add_argument("--warmup", type=positive_number, default=2)
    parser.add_argument("--connections", type=int, default=100)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.connections < 1 or args.repetitions < 1:
        parser.error("connections and repetitions must be greater than zero")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Record reproducibility metadata before attempting any worker measurement.
    report = {
        "schema_version": 1,
        "platform": os.environ.get("RUNNER_OS", platform.system()),
        "environment": {
            "os": platform.platform(),
            "architecture": platform.machine(),
            "cpu": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "python": platform.python_version(),
            "orionis": version("orionis"),
            "granian": version("granian"),
            "oha": OHA_VERSION,
            "commit": os.environ.get("GITHUB_SHA", "local"),
            "run_url": (
                f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
                f"{os.environ.get('GITHUB_RUN_ID', '')}"
                if os.environ.get("GITHUB_RUN_ID")
                else ""
            ),
        },
        "settings": {
            "duration_seconds": args.duration,
            "warmup_seconds": args.warmup,
            "connections": args.connections,
            "repetitions": args.repetitions,
            "interface": "rsgi",
            "http": "1.1",
            "loop": "asyncio",
        },
        "results": [],
    }
    failure = False
    # Reuse one verified client binary across the requested worker matrix.
    try:
        with TemporaryDirectory(prefix="orionis-oha-") as temporary:
            oha = install_oha(Path(temporary))
            for workers in dict.fromkeys(args.workers):
                row = {"workers": workers}
                report["results"].append(row)
                # Publish unsupported Windows cases without fabricated metrics.
                if sys.platform == "win32" and workers > 1:
                    row.update(status="unsupported", reason=WINDOWS_LIMIT)
                    continue
                print(f"Benchmark: {workers} worker(s)", flush=True)
                try:
                    samples = benchmark_workers(oha, workers, args, output)
                    # Aggregate measured runs without including warmup samples.
                    row.update(
                        status="failed" if any(s["errors"] for s in samples) else "ok",
                        samples=samples,
                        requests_per_second=statistics.median(
                            s["requests_per_second"] for s in samples
                        ),
                        mean_latency_ms=statistics.median(
                            s["mean_latency_ms"] for s in samples
                        ),
                        p95_latency_ms=statistics.median(
                            s["p95_latency_ms"] for s in samples
                        ),
                        requests=sum(s["requests"] for s in samples),
                        errors=sum(s["errors"] for s in samples),
                    )
                    failure |= row["status"] != "ok"
                except (
                    OSError,
                    ValueError,
                    KeyError,
                    RuntimeError,
                    subprocess.SubprocessError,
                ) as error:
                    # Retain this worker failure and continue the remaining matrix.
                    row.update(status="failed", reason=str(error))
                    failure = True
                    print(
                        f"FAILED ({workers} workers): {error}",
                        file=sys.stderr,
                        flush=True,
                    )
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        # Surface setup failures in both the report and the command exit status.
        report["error"] = str(error)
        failure = True
        print(f"Benchmark setup failed: {error}", file=sys.stderr, flush=True)
    finally:
        # Persist usable results even when setup or an individual run fails.
        write_report(output, report, render_report([report]))
    return int(failure)

# Propagate the benchmark status to the calling shell or CI job.
if __name__ == "__main__":
    raise SystemExit(main())
