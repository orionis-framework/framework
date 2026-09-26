from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.testing import (
    Testing, VerbosityMode,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapTesting(Testing):
    # ----------------------------------------------------------------------------------
    # verbosity : int | VerbosityMode, optional
    # --- Level of detail in test output. 0: silent, 1: standard, 2: detailed.
    # --- Defaults to 2 (detailed).
    # ----------------------------------------------------------------------------------
    verbosity: int | VerbosityMode = field(
        default_factory=lambda: Env.get("TESTING_VERBOSITY", VerbosityMode.DETAILED),
    )

    # ----------------------------------------------------------------------------------
    # fail_fast : bool, optional
    # --- If True, stops execution at the first failure.
    # --- Defaults to False.
    # ----------------------------------------------------------------------------------
    fail_fast: bool = field(
        default_factory=lambda: Env.get("TESTING_FAIL_FAST", False),
    )

    # ----------------------------------------------------------------------------------
    # start_dir : str, optional
    # --- Directory to search for tests.
    # --- Defaults to 'tests'.
    # ----------------------------------------------------------------------------------
    start_dir: str = field(
        default_factory=lambda: Env.get("TESTING_START_DIR", "tests"),
    )

    # ----------------------------------------------------------------------------------
    # file_pattern : str, optional
    # --- Filename pattern to identify test files.
    # --- Defaults to 'test_*.py'.
    # ----------------------------------------------------------------------------------
    file_pattern: str = field(
        default_factory=lambda: Env.get("TESTING_FILE_PATTERN", "test_*.py"),
    )

    # ----------------------------------------------------------------------------------
    # method_pattern : str, optional
    # --- Pattern to filter specific test methods.
    # --- Defaults to 'test*'.
    # ----------------------------------------------------------------------------------
    method_pattern: str = field(
        default_factory=lambda: Env.get("TESTING_METHOD_PATTERN", "test*"),
    )

    # ----------------------------------------------------------------------------------
    # cache_results : bool, optional
    # --- If True, saves a JSON file with the test results.
    # --- Defaults to False.
    # ----------------------------------------------------------------------------------
    cache_results: bool = field(
        default_factory=lambda: Env.get("TESTING_CACHE_RESULTS", False),
    )
