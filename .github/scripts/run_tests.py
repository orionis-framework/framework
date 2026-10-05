# Write workflow groups and CLI status directly to the console.
# ruff: noqa: T201

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

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
            Module directory or root test file name.
        """
        if self.directory == "tests":
            return f"Root [{self.directory}/{self.pattern}]"
        return self.directory

def discover_suites(repo_root: Path) -> list[TestSuite]:
    """
    Discover module suites and individual root test files.

    Parameters
    ----------
    repo_root : Path
        Repository containing the tests directory.

    Returns
    -------
    list[TestSuite]
        Sorted module suites followed by sorted root test files.
    """
    test_root = repo_root / "tests"
    modules: set[str] = set()
    root_files: list[str] = []
    for path in test_root.rglob("test_*.py"):
        if not path.is_file():
            continue
        relative = path.relative_to(test_root)
        if len(relative.parts) == 1:
            root_files.append(relative.name)
        else:
            modules.add(relative.parts[0])

    suites = [TestSuite(f"tests/{name}") for name in sorted(modules)]
    suites.extend(TestSuite("tests", name) for name in sorted(root_files))
    return suites

def run_suites(
    repo_root: Path,
    suites: Sequence[TestSuite],
    *,
    verbosity: int = 1,
    continue_on_error: bool = False,
) -> int:
    """
    Execute isolated suites and retain the first failing exit code.

    Parameters
    ----------
    repo_root : Path
        Working directory containing the reactor entry point.
    suites : Sequence[TestSuite]
        Suites to execute in the supplied order.
    verbosity : int, optional
        Reactor output detail, by default 1.
    continue_on_error : bool, optional
        Run remaining suites after a failure, by default False.

    Returns
    -------
    int
        Zero on success, otherwise the first failing code or 1 for a signal.
    """
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    in_actions = environment.get("GITHUB_ACTIONS") == "true"
    failure = 0
    for suite in suites:
        heading = f"Run tests: {suite.label}"
        print(f"::group::{heading}" if in_actions else heading, flush=True)
        command = [
            sys.executable,
            "-B",
            "reactor",
            "test",
            f"--start-dir={suite.directory}",
            f"--file-pattern={suite.pattern}",
            f"--verbosity={verbosity}",
            "--fail-fast=1",
        ]
        try:
            # Launch the active interpreter with separate command arguments.
            result = subprocess.run(  # noqa: S603
                command, cwd=repo_root, env=environment, check=False,
            )
        finally:
            if in_actions:
                print("::endgroup::", flush=True)
        if result.returncode:
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
    argv : Sequence[str] or None, optional
        Command arguments, or process arguments when omitted.

    Returns
    -------
    int
        Suite exit status, or 2 if discovery or execution cannot start.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", dest="list_suites")
    parser.add_argument("--verbosity", type=int, choices=(0, 1, 2), default=2)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    suites = discover_suites(repo_root)
    if not suites:
        print("No test suites found under tests/.", file=sys.stderr)
        return 2
    if args.list_suites:
        for suite in suites:
            print(suite.label)
        print(f"{len(suites)} test suites discovered.")
        return 0
    try:
        return run_suites(
            repo_root,
            suites,
            verbosity=args.verbosity,
            continue_on_error=args.continue_on_error,
        )
    except OSError as error:
        print(f"Unable to start test suite: {error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
