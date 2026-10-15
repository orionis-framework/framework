import argparse
import hashlib
import http.client
import json
import math
import os
import platform
import random
import shutil
import signal
import socket
import subprocess
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import psutil

from benchmarks.http_compare.client import OHA_VERSION, install_oha, parse_measurement
from benchmarks.http_compare.report import (
    METRICS,
    aggregate_samples,
    write_json,
    write_reports,
)

# These commands run local, fixed benchmark applications, without a shell.
# ruff: noqa: S603, T201

REPO = Path(__file__).resolve().parents[2]
GRANIAN_VERSION = "2.8.4"
STARTUP_TIMEOUT = 60
HTTP_1_1 = 11
WINDOWS_LIMIT = "Granian cannot run multiple workers on Windows; use --workers 1."


@dataclass(frozen=True)
class Framework:
    """Describe an application factory and its native server interface."""

    name: str
    interface: str
    module: str

    @property
    def target(self) -> str:
        """
        Return the application factory import target passed to Granian.

        Returns
        -------
        str
            Fully qualified module and factory name for this framework.
        """
        # Resolve the target without importing optional framework dependencies.
        return f"benchmarks.http_compare.apps.{self.module}:create_application"


FRAMEWORKS = {
    item.name: item
    for item in (
        Framework("orionis-rsgi", "rsgi", "orionis"),
        Framework("orionis-asgi", "asgi", "orionis"),
        Framework("fastapi", "asgi", "fastapi"),
        Framework("litestar", "asgi", "litestar"),
        Framework("starlette", "asgi", "starlette"),
    )
}


def positive_number(value: str) -> float:
    """
    Parse a finite positive duration in seconds.

    Parameters
    ----------
    value : str
        Command-line duration to convert.

    Returns
    -------
    float
        Finite duration greater than zero.

    Raises
    ------
    argparse.ArgumentTypeError
        If the parsed duration is nonfinite or nonpositive.
    ValueError
        If the value cannot be parsed as a float.
    """
    # Reject invalid durations before constructing load-generator arguments.
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        error_msg = "must be finite and greater than zero"
        raise argparse.ArgumentTypeError(error_msg)
    return number


def positive_integer(value: str) -> int:
    """
    Parse a positive connection or repetition count.

    Parameters
    ----------
    value : str
        Command-line count to convert.

    Returns
    -------
    int
        Count greater than zero.

    Raises
    ------
    argparse.ArgumentTypeError
        If the parsed count is nonpositive.
    ValueError
        If the value cannot be parsed as an integer.
    """
    # Exclude empty load configurations before starting any server process.
    number = int(value)
    if number < 1:
        error_msg = "must be greater than zero"
        raise argparse.ArgumentTypeError(error_msg)
    return number


def build_parser() -> argparse.ArgumentParser:
    """
    Build the comparison command-line parser without importing applications.

    Returns
    -------
    argparse.ArgumentParser
        Parser for framework selection, worker counts, load, and output settings.
    """
    # Keep argument parsing and --help independent of optional framework imports.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workers", type=int, nargs="+", choices=range(1, 5), default=[1, 2, 3, 4],
    )
    parser.add_argument(
        "--frameworks", nargs="+", choices=FRAMEWORKS, default=list(FRAMEWORKS),
    )
    parser.add_argument("--duration", type=positive_number, default=10)
    parser.add_argument("--warmup", type=positive_number, default=2)
    parser.add_argument("--connections", type=positive_integer, default=100)
    parser.add_argument("--repetitions", type=positive_integer, default=3)
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Seed for framework order per worker count",
    )
    parser.add_argument(
        "--oha",
        type=Path,
        help="Path to oha 1.16.0 (otherwise PATH or verified download)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark-results/http-compare"),
        help="New or empty directory",
    )
    return parser


def _git(*arguments: str) -> str:
    """
    Read repository metadata through a bounded Git command.

    Parameters
    ----------
    *arguments : str
        Git subcommand and arguments to execute from the repository root.

    Returns
    -------
    str
        Stripped output, or ``unknown`` if Git is absent or exits unsuccessfully.
    """
    # Keep unavailable Git metadata distinct from an empty successful response.
    executable = shutil.which("git")
    if executable is None:
        return "unknown"
    result = subprocess.run(
        [executable, *arguments],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def collect_environment() -> dict[str, Any]:
    """
    Collect actual runtime, hardware, dependency, and source metadata.

    Returns
    -------
    dict[str, Any]
        Reproducibility metadata, including versions and the dependency lock hash.
    """
    # Record missing distributions without importing their benchmark applications.
    versions = {}
    for package in ("orionis", "granian", "fastapi", "litestar", "starlette"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not installed"
    versions["oha"] = "not verified"
    # Preserve unknown source state when Git metadata cannot be queried.
    try:
        commit = _git("rev-parse", "HEAD")
        dirty = bool(_git("status", "--porcelain"))
    except OSError, subprocess.SubprocessError:
        commit, dirty = "unknown", None
    cpu = platform.processor()
    # Prefer Linux's descriptive CPU model over its generic processor label.
    if sys.platform == "linux":
        with suppress(OSError):
            cpu = next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")
                ),
                cpu,
            )
    lock = REPO / "uv.lock"
    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "memory_bytes": psutil.virtual_memory().total,
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "versions": versions,
        "commit": commit,
        "dirty": dirty,
        "uv_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
        "dependencies": sorted(
            {
                f"{distribution.metadata['Name']}=={distribution.version}"
                for distribution in metadata.distributions()
            },
        ),
        "run_url": (
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
            f"{os.environ['GITHUB_RUN_ID']}"
            if os.environ.get("GITHUB_RUN_ID")
            else ""
        ),
    }


def server_command(framework: Framework, workers: int, port: int) -> list[str]:
    """
    Build a Granian command with shared comparison settings.

    Parameters
    ----------
    framework : Framework
        Application factory and native server interface to measure.
    workers : int
        Number of server worker processes.
    port : int
        Loopback TCP port on which to listen.

    Returns
    -------
    list[str]
        Shell-free command arguments for the active Python interpreter.
    """
    # Vary only the application, native interface, worker count, and listener port.
    return [
        sys.executable,
        "-B",
        "-m",
        "granian",
        framework.target,
        "--factory",
        "--interface",
        framework.interface,
        "--http",
        "1",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--workers",
        str(workers),
        "--runtime-threads",
        "1",
        "--loop",
        "asyncio",
        "--task-impl",
        "asyncio",
        "--http1-keep-alive",
        "--no-ws",
        "--no-access-log",
        "--log-level",
        "warning",
        "--no-reload",
        "--no-respawn-failed-workers",
        "--no-metrics",
    ]


def track_children(
    process: subprocess.Popen[bytes], known: dict[int, psutil.Process],
) -> None:
    """
    Retain worker identities before their supervisor can exit.

    Parameters
    ----------
    process : subprocess.Popen[bytes]
        Owned Granian supervisor process.
    known : dict[int, psutil.Process]
        Mapping updated with observed descendants, keyed by process ID.

    Returns
    -------
    None
        Update the mapping with descendants that are still observable.
    """
    # Retain process identities so orphaned workers remain safe cleanup targets.
    with suppress(psutil.NoSuchProcess):
        for child in psutil.Process(process.pid).children(recursive=True):
            known[child.pid] = child


def stop_server(
    process: subprocess.Popen[bytes], known: dict[int, psutil.Process] | None = None,
) -> None:
    """
    Stop and reap only the owned server process tree.

    Parameters
    ----------
    process : subprocess.Popen[bytes]
        Granian supervisor started by the comparison runner.
    known : dict[int, psutil.Process] | None, optional
        Previously observed descendants, including workers already orphaned.

    Returns
    -------
    None
        Terminate the owned process group or Windows descendant tree.

    Raises
    ------
    RuntimeError
        If tracked Windows processes survive cleanup.
    subprocess.TimeoutExpired
        If the supervisor does not exit within the final wait period.
    """
    if sys.platform != "win32":
        # A dedicated session also retains ownership of orphaned worker processes.
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        finally:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        return
    # Preserve known descendants even when their original supervisor has exited.
    owned = dict(known or {})
    track_children(process, owned)
    with suppress(psutil.NoSuchProcess):
        parent = psutil.Process(process.pid)
        owned[parent.pid] = parent
        parent.terminate()
    for child in owned.values():
        with suppress(psutil.NoSuchProcess):
            child.terminate()
    # Escalate only for owned processes that survive graceful termination.
    _, alive = psutil.wait_procs(list(owned.values()), timeout=5)
    for child in alive:
        with suppress(psutil.NoSuchProcess):
            child.kill()
    _, survivors = psutil.wait_procs(alive, timeout=5)
    process.wait(timeout=5)
    if survivors:
        error_msg = (
            f"Server processes did not exit: {[child.pid for child in survivors]}"
        )
        raise RuntimeError(error_msg)


def check_workers(
    process: subprocess.Popen[bytes], ready: Path, workers: int,
    known: dict[int, psutil.Process],
) -> None:
    """
    Verify that every readiness marker belongs to an owned live worker.

    Parameters
    ----------
    process : subprocess.Popen[bytes]
        Owned Granian supervisor process.
    ready : Path
        Directory containing process-specific startup markers.
    workers : int
        Expected number of live worker processes.
    known : dict[int, psutil.Process]
        Mapping updated with owned descendants before validating markers.

    Returns
    -------
    None
        Confirm the supervisor and all expected workers are alive.

    Raises
    ------
    RuntimeError
        If the supervisor exits or markers do not match owned live workers.
    """
    # Files alone cannot establish readiness; verify process ownership and health.
    track_children(process, known)
    if process.poll() is not None:
        error_msg = f"Granian exited with code {process.returncode}; see server log"
        raise RuntimeError(error_msg)
    markers = list(ready.glob("*"))
    if len(markers) != workers:
        error_msg = f"Expected {workers} worker startup markers; found {len(markers)}"
        raise RuntimeError(error_msg)
    for marker in markers:
        worker = known.get(int(marker.name))
        alive = False
        if worker is not None:
            with suppress(psutil.NoSuchProcess):
                alive = worker.is_running() and worker.status() != psutil.STATUS_ZOMBIE
        if not alive:
            error_msg = (
                f"Worker {marker.name} exited or does not belong to this server"
            )
            raise RuntimeError(error_msg)


def wait_until_ready( # NOSONAR
    process: subprocess.Popen[bytes], port: int, ready: Path, workers: int,
    known: dict[int, psutil.Process],
) -> None:
    """
    Wait for healthy workers and verify the exact keep-alive response.

    Parameters
    ----------
    process : subprocess.Popen[bytes]
        Owned Granian supervisor process.
    port : int
        Loopback TCP port to probe.
    ready : Path
        Directory containing worker startup markers.
    workers : int
        Expected number of ready workers.
    known : dict[int, psutil.Process]
        Mapping updated with observed server descendants.

    Returns
    -------
    None
        Confirm worker health and two exact HTTP/1.1 keep-alive responses.

    Raises
    ------
    RuntimeError
        If a process fails or the endpoint returns an unexpected response.
    TimeoutError
        If all workers and the endpoint are not ready before the deadline.
    """
    # Verify worker ownership before probing HTTP to avoid false readiness.
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        track_children(process, known)
        if process.poll() is not None:
            error_msg = (
                f"Granian exited with code {process.returncode}; see server log"
            )
            raise RuntimeError(error_msg)
        if len(list(ready.glob("*"))) == workers:
            check_workers(process, ready, workers, known)
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            try:
                # Two requests on the same connection verify the keep-alive path.
                for _ in range(2):
                    connection.request("GET", "/")
                    response = connection.getresponse()
                    body = response.read()
                    content_type = (
                        response.getheader("content-type", "").split(";", 1)[0].lower()
                    )
                    if (
                        response.status != HTTPStatus.OK
                        or body != b"Hello World"
                        or content_type != "text/plain"
                    ):
                        error_msg = (
                            f"Unexpected response: {response.status}, "
                            f"{content_type}, {body!r}"
                        )
                        raise RuntimeError(error_msg)
                    if response.version != HTTP_1_1 or response.will_close:
                        error_msg = "Endpoint did not preserve HTTP/1.1 keep-alive"
                        raise RuntimeError(error_msg)
                return
            except OSError, http.client.HTTPException:
                # Retry transient connection errors while startup completes.
                pass
            finally:
                connection.close()
        time.sleep(0.1)
    error_msg = f"Not all {workers} workers became ready within {STARTUP_TIMEOUT}s"
    raise TimeoutError(error_msg)


def run_load(  # noqa: PLR0913
    oha: Path,
    url: str,
    seconds: float,
    connections: int,
    output: Path,
    commands: list[dict[str, Any]],
) -> dict[str, int | float]:
    """
    Run oha and preserve its command and output before parsing measurements.

    Parameters
    ----------
    oha : Path
        Verified load-generator executable.
    url : str
        HTTP endpoint to measure.
    seconds : float
        Nominal duration of the load run.
    connections : int
        Number of concurrent HTTP/1.1 connections.
    output : Path
        Raw JSON destination, also used to name the stderr log.
    commands : list[dict[str, Any]]
        Invocation log to update with the executed command.

    Returns
    -------
    dict[str, int | float]
        Normalized successful throughput, errors, elapsed time, and latency.

    Raises
    ------
    subprocess.CalledProcessError
        If oha exits unsuccessfully.
    subprocess.TimeoutExpired
        If execution exceeds the duration plus its shutdown allowance.
    ValueError
        If the output is invalid JSON or cannot define a valid measurement.
    """
    # Wait for in-flight requests so elapsed time includes their completion.
    command = [
        str(oha),
        "--no-tui",
        "--output-format",
        "json",
        "--http-version",
        "1.1",
        "--worker-threads",
        "1",
        "--wait-ongoing-requests-after-deadline",
        "-t",
        "5s",
        "-c",
        str(connections),
        "-z",
        f"{seconds}s",
        url,
    ]
    commands.append({"kind": "oha", "argv": command, "output": str(output)})
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=seconds + 30,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except subprocess.TimeoutExpired as error:
        # Preserve partial evidence before propagating a load-generator timeout.
        output.write_bytes(error.stdout or b"")
        output.with_suffix(".stderr.log").write_bytes(error.stderr or b"")
        raise
    # Save both streams before exit-status checks or parsing can raise an error.
    output.write_text(result.stdout, encoding="utf-8")
    output.with_suffix(".stderr.log").write_text(result.stderr, encoding="utf-8")
    result.check_returncode()
    return parse_measurement(json.loads(result.stdout))


def benchmark_case(  # noqa: PLR0913
    framework: Framework,
    workers: int,
    args: argparse.Namespace,
    oha: Path,
    output: Path,
    commands: list[dict[str, Any]],
    row: dict[str, Any],
) -> None:
    """
    Warm up and measure one configuration while retaining failure evidence.

    Parameters
    ----------
    framework : Framework
        Application factory and native server interface to measure.
    workers : int
        Number of Granian worker processes.
    args : argparse.Namespace
        Parsed warmup, duration, connection, and repetition settings.
    oha : Path
        Verified load-generator executable.
    output : Path
        Report directory with existing ``raw`` and ``logs`` subdirectories.
    commands : list[dict[str, Any]]
        Invocation log updated with server and load-generator commands.
    row : dict[str, Any]
        Result row updated with warmup, samples, status, and valid metrics.

    Returns
    -------
    None
        Update the supplied row and always attempt server-tree cleanup.
    """
    # Isolate application files and readiness markers for every configuration.
    prefix = f"{framework.name}-workers-{workers}"
    with TemporaryDirectory(prefix="http-compare-app-") as temporary:
        directory = Path(temporary)
        ready = directory / "worker-ready"
        ready.mkdir()
        # Ask the OS for a listener port instead of sharing a fixed benchmark port.
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]
        command = server_command(framework, workers, port)
        commands.append({"kind": "server", "argv": command, "cwd": str(directory)})
        # Avoid inherited server tuning or a developer .env altering one case.
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GRANIAN_")
        }
        environment.update(
            {
                "PYTHONPATH": str(REPO),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
                "BENCHMARK_READY_DIR": str(ready),
                "APP_KEY": "0123456789abcdef0123456789abcdef",
                "APP_ENV": "production",
                "APP_DEBUG": "false",
                "NO_PROXY": "127.0.0.1,localhost",
            },
        )
        with (output / "logs" / f"{prefix}.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=directory,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=sys.platform != "win32",
                creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32"
                else 0,
            )
            known = {}
            try:
                wait_until_ready(process, port, ready, workers, known)
                url = f"http://127.0.0.1:{port}/"
                # Preserve warmup separately so it cannot affect measured totals.
                row["warmup"] = run_load(
                    oha,
                    url,
                    args.warmup,
                    args.connections,
                    output / "raw" / f"{prefix}-warmup.json",
                    commands,
                )
                if row["warmup"]["errors"]:
                    error_msg = "Warmup returned HTTP or transport errors"
                    raise RuntimeError(error_msg)
                check_workers(process, ready, workers, known)
                samples = row.setdefault("samples", [])
                # Recheck worker health after each run before publishing medians.
                for repetition in range(1, args.repetitions + 1):
                    sample = run_load(
                        oha,
                        url,
                        args.duration,
                        args.connections,
                        output / "raw" / f"{prefix}-run-{repetition}.json",
                        commands,
                    )
                    samples.append(sample)
                    check_workers(process, ready, workers, known)
                row.update(aggregate_samples(samples))
            finally:
                # Clean up even when readiness, warmup, or measurement fails.
                stop_server(process, known)


def resolve_oha(explicit: Path | None, directory: Path) -> Path:
    """
    Locate or download oha and require the pinned version.

    Parameters
    ----------
    explicit : Path | None
        Explicit executable path, or ``None`` to search PATH before downloading.
    directory : Path
        Existing temporary directory used if a download is needed.

    Returns
    -------
    Path
        Executable path whose reported version matches the pinned release.

    Raises
    ------
    RuntimeError
        If the binary version, platform, or download verification is invalid.
    subprocess.SubprocessError
        If querying the executable version fails.
    """
    # Prefer an explicit binary, then PATH, then a verified temporary download.
    found = shutil.which("oha") if explicit is None else None
    if explicit is not None:
        path = explicit.resolve()
    elif found:
        path = Path(found)
    else:
        path = install_oha(directory)
    result = subprocess.run(
        [str(path), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.stdout.strip() != f"oha {OHA_VERSION}":
        error_msg = f"Expected oha {OHA_VERSION}; found {result.stdout.strip()!r}"
        raise RuntimeError(error_msg)
    return path


def main(argv: list[str] | None = None) -> int:  # noqa: C901, PLR0912, PLR0915 # NOSONAR
    """
    Run the requested comparison matrix and persist partial failure reports.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments, or ``None`` to read the process arguments.

    Returns
    -------
    int
        Zero if every requested case succeeds, otherwise one.

    Raises
    ------
    SystemExit
        If argument parsing or output-directory validation fails.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    # Reject stale destinations before creating any benchmark artifacts.
    output = args.output_dir.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error(
            "--output-dir must be a new or empty directory to avoid stale results",
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "raw").mkdir()
    (output / "logs").mkdir()
    # Record shared settings once so every case uses the same measurement policy.
    report = {
        "schema_version": 1,
        "environment": collect_environment(),
        "settings": {
            "workers": list(dict.fromkeys(args.workers)),
            "frameworks": list(dict.fromkeys(args.frameworks)),
            "duration_seconds": args.duration,
            "warmup_seconds": args.warmup,
            "connections": args.connections,
            "repetitions": args.repetitions,
            "http": "1.1",
            "keep_alive": True,
            "loop": "asyncio",
            "runtime_threads": 1,
            "oha_worker_threads": 1,
            "wait_ongoing_requests": True,
            "seed": args.seed,
        },
        "execution_order": [],
        "results": [],
    }
    commands = []
    failed = False
    try:
        if report["environment"]["versions"]["granian"] != GRANIAN_VERSION:
            error_msg = (
                f"Granian {GRANIAN_VERSION} required; "
                "run uv sync --locked --group benchmark"
            )
            raise RuntimeError(error_msg)
        with TemporaryDirectory(prefix="http-compare-oha-") as temporary:
            oha = resolve_oha(args.oha, Path(temporary))
            report["environment"]["versions"]["oha"] = OHA_VERSION
            report["environment"]["oha_executable"] = str(oha)
            # Shuffle reproducibly within each worker count to reduce order bias.
            generator = random.Random(args.seed)  # noqa: S311
            for workers in report["settings"]["workers"]:
                names = list(report["settings"]["frameworks"])
                generator.shuffle(names) # NOSONAR
                for name in names:
                    framework = FRAMEWORKS[name]
                    row = {
                        "framework": name,
                        "interface": framework.interface,
                        "workers": workers,
                        "status": "pending",
                    }
                    report["results"].append(row)
                    report["execution_order"].append(
                        {"framework": name, "workers": workers},
                    )
                    # Do not publish Windows' single-worker fallback as scaling.
                    if sys.platform == "win32" and workers > 1:
                        row.update(status="unsupported", reason=WINDOWS_LIMIT)
                        failed = True
                        continue
                    print(f"Benchmark: {name}, {workers} worker(s)", flush=True)
                    try:
                        benchmark_case(
                            framework, workers, args, oha, output, commands, row,
                        )
                    except (
                        OSError,
                        ValueError,
                        KeyError,
                        TypeError,
                        RuntimeError,
                        subprocess.SubprocessError,
                        psutil.Error,
                    ) as error:
                        row.update(status="failed", reason=str(error))
                        # Cleanup or later failures invalidate earlier medians.
                        for metric in METRICS:
                            row.pop(metric, None)
                        print(
                            f"FAILED: {name}, {workers} workers: {error}",
                            file=sys.stderr,
                            flush=True,
                        )
                    failed |= row["status"] != "ok"
                    write_reports(output, report)
                    write_json(output / "commands.json", commands)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        subprocess.SubprocessError,
        psutil.Error,
    ) as error:
        # Distinguish setup failures from failures inside individual cases.
        report["error"] = str(error)
        failed = True
        print(f"Benchmark setup failed: {error}", file=sys.stderr, flush=True)
    except KeyboardInterrupt:
        # Retain completed measurements while marking the active case as failed.
        report["error"] = "Interrupted by user"
        for row in report["results"]:
            if row["status"] == "pending":
                row.update(status="failed", reason="Interrupted by user")
        failed = True
    finally:
        # Flush artifacts and the Actions summary even after setup or case errors.
        markdown = write_reports(output, report)
        write_json(output / "commands.json", commands)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with Path(summary).open("a", encoding="utf-8") as stream:
                stream.write(markdown)
        print(markdown)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
