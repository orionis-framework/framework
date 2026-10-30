import argparse
import hashlib
import http.client
import json
import math
import os
import platform
import random
import re
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
    FAILED_COMPARISON,
    METRICS,
    aggregate_samples,
    render_throughput_svg,
    write_json,
    write_reports,
)

# These commands run local, fixed benchmark applications, without a shell.
# ruff: noqa: S603, T201

REPO = Path(__file__).resolve().parents[2]
SERVER_VERSIONS = {"granian": "2.8.4", "uvicorn": "0.54.0"}
STARTUP_TIMEOUT = 60
HTTP_1_1 = 11
WINDOWS_LIMIT = (
    "Multi-worker HTTP comparisons are unsupported on Windows; use --workers 1."
)
PROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
BENCHMARK_ERRORS = (
    OSError,
    ValueError,
    KeyError,
    TypeError,
    RuntimeError,
    subprocess.SubprocessError,
    psutil.Error,
)

@dataclass(frozen=True)
class Framework:
    """Describe an application factory and its native server interface."""

    name: str
    interface: str
    module: str

    @property
    def target(self) -> str:
        """Return the factory target without importing optional frameworks."""
        return f"benchmarks.http_compare.apps.{self.module}:create_application"

    @property
    def server(self) -> str:
        """Use Granian for Orionis and Uvicorn for the other frameworks."""
        return "granian" if self.module == "orionis" else "uvicorn"

    @property
    def requires_warmup(self) -> bool:
        """Enable HTTP preparation and load warmup only for Orionis."""
        return self.module == "orionis"

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
    """Parse a finite positive duration in seconds."""
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        error_msg = "must be finite and greater than zero"
        raise argparse.ArgumentTypeError(error_msg)
    return number

def positive_integer(value: str) -> int:
    """Parse a positive connection or repetition count."""
    number = int(value)
    if number < 1:
        error_msg = "must be greater than zero"
        raise argparse.ArgumentTypeError(error_msg)
    return number

def build_parser() -> argparse.ArgumentParser:
    """Build the comparison CLI without importing benchmark applications."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workers", type=int, nargs="+", choices=range(1, 5), default=[1, 2, 3, 4],
    )
    parser.add_argument(
        "--frameworks", nargs="+", choices=FRAMEWORKS, default=list(FRAMEWORKS),
    )
    parser.add_argument("--duration", type=positive_number, default=10)
    parser.add_argument(
        "--warmup", type=positive_number, default=2,
        help=argparse.SUPPRESS,
    )
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
    """Read Git metadata, reporting unavailable values as unknown."""
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
        creationflags=PROCESS_FLAGS,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"

def collect_environment() -> dict[str, Any]:
    """Collect runtime, hardware, dependencies and source provenance."""
    versions = {}
    for package in ("orionis", *SERVER_VERSIONS, "fastapi", "litestar", "starlette"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not installed"
    versions["oha"] = "not verified"
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

def check_server_versions(frameworks: list[str], versions: dict[str, str]) -> None:
    """Require the pinned versions of the servers selected for this run."""
    for server in dict.fromkeys(FRAMEWORKS[name].server for name in frameworks):
        version = SERVER_VERSIONS[server]
        if versions[server] != version:
            error_msg = (
                f"{server.capitalize()} {version} required; "
                "run uv sync --locked --group benchmark"
            )
            raise RuntimeError(error_msg)

def server_command(framework: Framework, workers: int, port: int) -> list[str]:
    """Build the assigned server command with matching HTTP and load settings."""
    command = [
        sys.executable, "-B", "-m", framework.server,
        framework.target,
        "--factory",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--workers", str(workers),
        "--loop", "asyncio",
        "--no-access-log",
        "--log-level", "info",
    ]
    if framework.server == "granian":
        command.extend([
            "--interface", framework.interface,
            "--http", "1",
            "--runtime-threads", "1",
            "--task-impl", "asyncio",
            "--http1-keep-alive",
            "--no-ws",
            "--no-reload",
            "--no-respawn-failed-workers",
            "--no-metrics",
        ])
    else:
        command.extend([
            "--http", "h11",
            "--ws", "none",
            "--lifespan", "on",
            "--no-use-colors",
        ])
    return command

def track_children(
    process: subprocess.Popen[bytes], known: dict[int, psutil.Process],
) -> None:
    """Retain owned worker identities for cleanup even after they are orphaned."""
    with suppress(psutil.NoSuchProcess):
        for child in psutil.Process(process.pid).children(recursive=True):
            known[child.pid] = child

def stop_server(
    process: subprocess.Popen[bytes], known: dict[int, psutil.Process] | None = None,
) -> None:
    """Terminate and reap only the owned server process tree."""
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
    owned = dict(known or {})
    track_children(process, owned)
    with suppress(psutil.NoSuchProcess):
        owned = {process.pid: psutil.Process(process.pid), **owned}
    for child in owned.values():
        with suppress(psutil.NoSuchProcess):
            child.terminate()
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
    process: subprocess.Popen[bytes], worker_pids: set[int],
    known: dict[int, psutil.Process],
) -> None:
    """Require every worker announced by the server to remain alive and owned."""
    track_children(process, known)
    if process.poll() is not None:
        error_msg = f"Server exited with code {process.returncode}; see server log"
        raise RuntimeError(error_msg)
    if not worker_pids:
        error_msg = "Server has not announced any started workers"
        raise RuntimeError(error_msg)
    for pid in worker_pids:
        worker = known.get(pid)
        alive = False
        with suppress(psutil.NoSuchProcess):
            if pid == process.pid:
                worker = psutil.Process(pid)
            if worker is not None:
                alive = worker.is_running() and worker.status() != psutil.STATUS_ZOMBIE
        if not alive:
            error_msg = (
                f"Worker {pid} exited or does not belong to this server"
            )
            raise RuntimeError(error_msg)

def _probe_response(
    connection: http.client.HTTPConnection,
) -> None:
    """Validate an unmeasured Hello World response on a keep-alive connection."""
    connection.request("GET", "/")
    response = connection.getresponse()
    body = response.read()
    content_type = response.getheader("content-type", "").split(";", 1)[0].lower()
    if (
        response.status != HTTPStatus.OK
        or content_type != "text/plain"
        or body != b"Hello World"
    ):
        error_msg = (
            f"Unexpected response for /: {response.status}, "
            f"{content_type}, {body!r}"
        )
        raise RuntimeError(error_msg)
    if response.version != HTTP_1_1 or response.will_close:
        error_msg = "Endpoint did not preserve HTTP/1.1 keep-alive"
        raise RuntimeError(error_msg)

def started_workers(events: str, framework: Framework) -> set[int]:
    """Read native worker PIDs only after their application startup completes."""
    if framework.server == "uvicorn":
        pids = {
            int(pid)
            for pid in re.findall(r"Started server process \[(\d+)\]\r?\n", events)
        }
        completed = re.findall(r"Application startup complete\.\r?\n", events)
        return pids if len(completed) == len(pids) else set()
    started = set(re.findall(r"Started worker-(\d+)\r?\n", events))
    return {
        int(pid)
        for index, pid in re.findall(
            r"Spawning worker-(\d+) with PID: (\d+)\r?\n", events,
        )
        if index in started
    }

def wait_until_ready(  # noqa: PLR0913
    process: subprocess.Popen[bytes], port: int, log_path: Path, workers: int,
    known: dict[int, psutil.Process], *, framework: Framework,
) -> set[int]:
    """Wait for native server startup, probing HTTP only for Orionis."""
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        track_children(process, known)
        if process.poll() is not None:
            error_msg = (
                f"{framework.server.capitalize()} exited with code "
                f"{process.returncode}; see server log"
            )
            raise RuntimeError(error_msg)
        events = log_path.read_text(encoding="utf-8")
        worker_pids = started_workers(events, framework)
        if len(worker_pids) != workers:
            time.sleep(0.1)
            continue
        check_workers(process, worker_pids, known)
        try:
            if framework.requires_warmup:
                connection = http.client.HTTPConnection(
                    "127.0.0.1", port, timeout=1,
                )
                try:
                    for _ in range(2):
                        _probe_response(connection)
                finally:
                    connection.close()
            else:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
            check_workers(process, worker_pids, known)
            return worker_pids
        except OSError, http.client.HTTPException:
            # Retry transient connection errors while startup completes.
            pass
        time.sleep(0.1)
    error_msg = (
        f"{framework.server.capitalize()} did not start {workers} ready workers within "
        f"{STARTUP_TIMEOUT}s; see server log"
    )
    raise TimeoutError(error_msg)

def run_load(  # noqa: PLR0913
    oha: Path,
    url: str,
    seconds: float,
    connections: int,
    output: Path,
    commands: list[dict[str, Any]],
) -> dict[str, int | float]:
    """Run oha with direct diagnostic files and return normalized measurements."""
    command = [
        str(oha),
        "--no-tui",
        "--output-format", "json",
        "--http-version", "1.1",
        "--worker-threads", "1",
        "--wait-ongoing-requests-after-deadline",
        "-t", "5s",
        "-c", str(connections),
        "-z", f"{seconds}s",
        url,
    ]
    commands.append({"kind": "oha", "argv": command, "output": str(output)})
    with (
        output.open("w+", encoding="utf-8") as stdout,
        output.with_suffix(".stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        subprocess.run(
            command,
            stdout=stdout,
            stderr=stderr,
            timeout=seconds + 30,
            check=True,
            creationflags=PROCESS_FLAGS,
        )
        stdout.seek(0)
        return parse_measurement(json.load(stdout))

def benchmark_case(  # noqa: PLR0913
    framework: Framework,
    workers: int,
    args: argparse.Namespace,
    oha: Path,
    output: Path,
    commands: list[dict[str, Any]],
    row: dict[str, Any],
) -> None:
    """Measure an isolated server, warming only Orionis and always cleaning up."""
    prefix = f"{framework.name}-workers-{workers}"
    with TemporaryDirectory(prefix="http-compare-app-") as temporary:
        directory = Path(temporary)
        if framework.module == "orionis":
            shutil.copyfile(
                REPO / "benchmarks" / "http_compare" / "apps" / "routes" / "web.py",
                directory / "_http_compare_routes.py",
            )
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]
        command = server_command(framework, workers, port)
        commands.append({"kind": "server", "argv": command, "cwd": str(directory)})
        # Avoid inherited server tuning or a developer .env altering one case.
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GRANIAN_", "UVICORN_"))
        }
        environment.update(
            PYTHONPATH=str(REPO),
            PYTHONIOENCODING="utf-8",
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONHASHSEED="0",
            APP_KEY="0123456789abcdef0123456789abcdef",
            APP_ENV="production",
            APP_DEBUG="false",
            NO_PROXY="127.0.0.1,localhost",
        )
        log_path = output / "logs" / f"{prefix}.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=directory,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=sys.platform != "win32",
                creationflags=PROCESS_FLAGS,
            )
            known: dict[int, psutil.Process] = {}
            try:
                worker_pids = wait_until_ready(
                    process, port, log_path, workers, known,
                    framework=framework,
                )
                url = f"http://127.0.0.1:{port}/"
                if framework.requires_warmup:
                    row["warmup"] = run_load(
                        oha, url, args.warmup, args.connections,
                        output / "raw" / f"{prefix}-warmup.json",
                        commands,
                    )
                    if row["warmup"]["errors"]:
                        error_msg = "Warmup returned HTTP or transport errors"
                        raise RuntimeError(error_msg)
                    check_workers(process, worker_pids, known)
                samples = row.setdefault("samples", [])
                for repetition in range(1, args.repetitions + 1):
                    samples.append(run_load(
                        oha, url, args.duration, args.connections,
                        output / "raw" / f"{prefix}-run-{repetition}.json",
                        commands,
                    ))
                    check_workers(process, worker_pids, known)
                row.update(aggregate_samples(samples))
            finally:
                stop_server(process, known)

def resolve_oha(explicit: Path | None, directory: Path) -> Path:
    """Locate or download oha and verify its pinned version."""
    if explicit is not None:
        path = explicit.resolve()
    elif found := shutil.which("oha"):
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
        creationflags=PROCESS_FLAGS,
    )
    if result.stdout.strip() != f"oha {OHA_VERSION}":
        error_msg = f"Expected oha {OHA_VERSION}; found {result.stdout.strip()!r}"
        raise RuntimeError(error_msg)
    return path

def _run_matrix(
    args: argparse.Namespace,
    oha: Path,
    output: Path,
    report: dict[str, Any],
    commands: list[dict[str, Any]],
) -> None:
    """Run shuffled cases sequentially, preserving failures and partial results."""
    settings = report["settings"]
    # Seeded benchmark ordering is reproducible and not security-sensitive.
    generator = random.Random(args.seed)  # noqa: S311
    for workers in settings["workers"]:
        names = list(settings["frameworks"])
        generator.shuffle(names)  # NOSONAR(S2245)
        for name in names:
            framework = FRAMEWORKS[name]
            row = {
                "framework": name,
                "interface": framework.interface,
                "workers": workers,
                "status": "pending",
            }
            report["results"].append(row)
            report["execution_order"].append({"framework": name, "workers": workers})
            if sys.platform == "win32" and workers > 1:
                row.update(status="unsupported", reason=WINDOWS_LIMIT)
                continue
            print(f"Benchmark: {name}, {workers} worker(s)", flush=True)
            try:
                benchmark_case(framework, workers, args, oha, output, commands, row)
            except BENCHMARK_ERRORS as error:
                row.update(status="failed", reason=str(error))
                # Cleanup failures also invalidate previously computed metrics.
                for metric in METRICS:
                    row.pop(metric, None)
                print(
                    f"FAILED: {name}, {workers} workers. {FAILED_COMPARISON}",
                    file=sys.stderr,
                    flush=True,
                )
            write_reports(output, report)
            write_json(output / "commands.json", commands)

def main(argv: list[str] | None = None) -> int:
    """Run the comparison CLI and persist reports, including partial failures."""
    parser = build_parser()
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error(
            "--output-dir must be a new or empty directory to avoid stale results",
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "raw").mkdir()
    (output / "logs").mkdir()
    frameworks = list(dict.fromkeys(args.frameworks))
    report: dict[str, Any] = {
        "schema_version": 1,
        "environment": collect_environment(),
        "settings": {
            "workers": list(dict.fromkeys(args.workers)),
            "frameworks": frameworks,
            "servers": {name: FRAMEWORKS[name].server for name in frameworks},
            "duration_seconds": args.duration,
            "warmup_seconds": args.warmup,
            "warmup_frameworks": [
                name for name in frameworks
                if FRAMEWORKS[name].requires_warmup
            ],
            "connections": args.connections,
            "repetitions": args.repetitions,
            "http": "1.1",
            "keep_alive": True,
            "loop": "asyncio",
            "runtime_threads": 1,
            "oha_worker_threads": 1,
            "wait_ongoing_requests": True,
            "readiness": "native-server-workers-and-tcp",
            "seed": args.seed,
        },
        "execution_order": [],
        "results": [],
    }
    commands: list[dict[str, Any]] = []
    try:
        check_server_versions(frameworks, report["environment"]["versions"])
        with TemporaryDirectory(prefix="http-compare-oha-") as temporary:
            oha = resolve_oha(args.oha, Path(temporary))
            report["environment"]["versions"]["oha"] = OHA_VERSION
            report["environment"]["oha_executable"] = str(oha)
            _run_matrix(args, oha, output, report, commands)
    except BENCHMARK_ERRORS as error:
        report["error"] = str(error)
        print(FAILED_COMPARISON, file=sys.stderr, flush=True)
    except KeyboardInterrupt:
        report["error"] = "Interrupted by user"
        for row in report["results"]:
            if row["status"] == "pending":
                row.update(status="failed", reason="Interrupted by user")
    finally:
        markdown = write_reports(output, report)
        write_json(output / "commands.json", commands)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with Path(summary).open("a", encoding="utf-8") as stream:
                stream.write(markdown)
        print(markdown)
    if "error" in report or any(
        row["status"] != "ok" for row in report["results"]
    ):
        return 1
    for workers in report["settings"]["workers"]:
        (output / f"throughput-{workers}-workers.svg").write_text(
            render_throughput_svg(report, workers), encoding="utf-8",
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
