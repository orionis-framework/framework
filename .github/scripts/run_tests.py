# ruff: noqa: S603, T201

import argparse
import ctypes
import fnmatch
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, TYPE_CHECKING

if sys.platform == "win32":
    import _winapi

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@dataclass(frozen=True, slots=True)
class TestSuite:
    """Describe a test directory and its optional root file filter."""

    directory: str
    pattern: str = "test_*.py"

    @property
    def label(self) -> str:
        """
        Return the suite path displayed in local and CI logs.

        Returns
        -------
        str
            Module directory, or a root label containing the file pattern.
        """
        # Distinguish root test files that otherwise share the same directory.
        if self.directory == "tests":
            return f"Root [{self.directory}/{self.pattern}]"
        return self.directory


def _raise_discovery_error(error: OSError) -> NoReturn:
    """
    Propagate traversal errors instead of silently omitting test suites.

    Parameters
    ----------
    error : OSError
        Filesystem error reported by the directory walker.

    Raises
    ------
    OSError
        Always propagate the original error.
    """
    raise error


def discover_suites(repo_root: Path) -> list[TestSuite]:
    """
    Discover public test suites while excluding local real-database tests.

    Parameters
    ----------
    repo_root : Path
        Repository containing the tests directory.

    Returns
    -------
    list[TestSuite]
        Sorted module suites followed by sorted root test files.

    Raises
    ------
    OSError
        If an allowed suite directory cannot be read.
    """
    # Deduplicate nested module directories while retaining individual root files.
    test_root = repo_root / "tests"
    if not test_root.is_dir():
        return []
    modules: set[str] = set()
    root_files: list[str] = []
    for directory, children, filenames in test_root.walk(
        on_error=_raise_discovery_error,
    ):
        # Prune before walking: excluded files must never enter discovery.
        if directory == test_root and "real_database" in children:
            children.remove("real_database")
        for filename in filenames:
            if not fnmatch.fnmatch(filename, "test_*.py"):
                continue
            path = directory / filename
            if not path.is_file():
                continue
            relative = path.relative_to(test_root)
            if len(relative.parts) == 1:
                root_files.append(relative.name)
            else:
                modules.add(relative.parts[0])

    # Keep module and root-file execution order stable across platforms.
    suites = [TestSuite(f"tests/{name}") for name in sorted(modules)]
    suites.extend(TestSuite("tests", name) for name in sorted(root_files))
    return suites


def _short_path(directory: Path) -> Path:
    """Return the Windows short spelling of an existing directory.

    Parameters
    ----------
    directory : pathlib.Path
        Existing canonical directory to translate.

    Returns
    -------
    pathlib.Path
        Short path, or the unchanged path when 8.3 names are disabled.

    Raises
    ------
    OSError
        If Windows cannot query the directory spelling.
    """
    get_short_path_name = ctypes.windll.kernel32.GetShortPathNameW
    length = get_short_path_name(str(directory), None, 0)
    if not length:
        raise ctypes.WinError()
    buffer = ctypes.create_unicode_buffer(length)
    if not get_short_path_name(str(directory), buffer, length):
        raise ctypes.WinError()
    return Path(buffer.value)


@contextmanager
def _windows_temp_directory(*, enabled: bool) -> Iterator[Path | None]:
    """Exercise Windows aliases, spaces and Unicode in one test-suite pass.

    Parameters
    ----------
    enabled : bool
        Whether the caller requested the Windows temporary-path profile.

    Yields
    ------
    pathlib.Path or None
        Temporary alias retained until every subprocess finishes, or None
        when the profile is disabled or the operating system is not Windows.

    Raises
    ------
    OSError
        If the temporary directory or its alias cannot be prepared or removed.
    """
    if not enabled or sys.platform != "win32":
        yield None
        return
    with tempfile.TemporaryDirectory(prefix="orionis-ci-windows-") as name:
        root = Path(name).resolve()
        target = root / "target"
        target.mkdir()
        alias = _short_path(target)
        junction = root / "alias"
        use_junction = alias == target
        if use_junction:
            # A junction needs no administrator rights and works without 8.3.
            _winapi.CreateJunction(str(target), str(junction))
            alias = junction
        try:
            temporary = alias / "Temporary files ñ"
            temporary.mkdir()
            if temporary == temporary.resolve():
                message = "Windows temporary-path profile requires a real alias."
                raise OSError(message)
            print(f"Windows temporary directory: {temporary}", flush=True)
            yield temporary
        finally:
            # Remove the junction itself before cleaning the owned target tree.
            if use_junction:
                junction.rmdir()


def run_suites(
    repo_root: Path,
    suites: Sequence[TestSuite],
    *,
    verbosity: int = 1,
    continue_on_error: bool = False,
    temporary_directory: Path | None = None,
) -> int:
    """
    Run isolated suites and retain the first failing exit code.

    Parameters
    ----------
    repo_root : Path
        Working directory containing the reactor entry point.
    suites : Sequence[TestSuite]
        Suites to execute in the supplied order.
    verbosity : int, optional
        Reactor output detail, by default 1.
    continue_on_error : bool, optional
        Run remaining tests and suites after a failure, by default False.
    temporary_directory : pathlib.Path or None, optional
        TMPDIR, TEMP and TMP directory inherited by every test subprocess.

    Returns
    -------
    int
        Zero on success, otherwise the first failing code or 1 for a signal.
    """
    # Give child interpreters consistent encoding and preserve the caller's setup.
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if temporary_directory is not None:
        environment.update({
            "TMPDIR": str(temporary_directory),
            "TEMP": str(temporary_directory),
            "TMP": str(temporary_directory),
        })
    in_actions = environment.get("GITHUB_ACTIONS") == "true"
    failure = 0
    # Isolate suites in separate interpreters and group their CI log output.
    for suite in suites:
        heading = f"Run tests: {suite.label}"
        print(f"::group::{heading}" if in_actions else heading, flush=True)
        start_path = (
            f"{suite.directory}/{suite.pattern}"
            if suite.directory == "tests"
            else suite.directory
        )
        command = [
            sys.executable,
            "-B",
            "reactor",
            "test",
            f"--start-dir={start_path}",
            f"--file-pattern={suite.pattern}",
            f"--verbosity={verbosity}",
            f"--fail-fast={int(not continue_on_error)}",
        ]
        try:
            # Launch the active interpreter with separate command arguments.
            result = subprocess.run(
                command,
                cwd=repo_root,
                env=environment,
                check=False,
            )
        finally:
            if in_actions:
                print("::endgroup::", flush=True)
        if result.returncode:
            # Preserve the first failure and normalize negative signal statuses.
            failure = failure or max(result.returncode, 1)
            print(
                f"FAILED: {suite.label} (exit {result.returncode})",
                file=sys.stderr,
                flush=True,
            )
            if not continue_on_error:
                break
    return failure


def main(argv: Sequence[str] | None = None) -> int:
    """
    List or run every discovered repository test suite.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Command arguments, or process arguments when omitted.

    Returns
    -------
    int
        Zero on success, the first suite failure, or 2 on a startup failure.
    """
    # Use the same discovery rules for listing and execution.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", dest="list_suites")
    parser.add_argument("--verbosity", type=int, choices=(0, 1, 2), default=2)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--windows-temp",
        action="store_true",
        help="Exercise temporary path aliases, spaces and Unicode on Windows.",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    suites = discover_suites(repo_root)
    if not suites:
        # Treat an empty inventory as a configuration failure, not a passing run.
        print("No test suites found under tests/.", file=sys.stderr)
        return 2
    if args.list_suites:
        # Let callers inspect the inventory without launching test subprocesses.
        for suite in suites:
            print(suite.label)
        print(f"{len(suites)} test suites discovered.")
        return 0
    # Convert subprocess startup errors into an explicit CLI failure status.
    try:
        with _windows_temp_directory(enabled=args.windows_temp) as temporary:
            return run_suites(
                repo_root,
                suites,
                verbosity=args.verbosity,
                continue_on_error=args.continue_on_error,
                temporary_directory=temporary,
            )
    except OSError as error:
        print(f"Unable to start test suite: {error}", file=sys.stderr)
        return 2


# Propagate discovery and suite failures to the calling shell or CI job.
if __name__ == "__main__":
    raise SystemExit(main())
