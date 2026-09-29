from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.testing.enums import VerbosityMode
from orionis.foundation.config.validation import validate_boolean, validate_string
from orionis.foundation.config.validation import validate_integer
from orionis.support.entities.base import BaseEntity

# Pre-computed valid verbosity values: avoids building a list on every Testing() init.
_VERBOSITY_VALUES: frozenset[int] = frozenset(mode.value for mode in VerbosityMode)

@dataclass(frozen=True, kw_only=True)
class Testing(BaseEntity):
    """
    Configure testing settings.

    Parameters
    ----------
    verbosity : int | VerbosityMode
        Level of detail in test output. 0: silent, 1: standard, 2: detailed.
        Defaults to 2 (detailed).
    fail_fast : bool
        If True, stops execution at the first failure. Defaults to False.
    start_dir : str
        Directory to search for tests. Defaults to 'tests'.
    file_pattern : str
        Filename pattern to identify test files. Defaults to 'test_*.py'.
    method_pattern : str
        Pattern to filter specific test methods. Defaults to 'test*'.

    Returns
    -------
    None
        Instantiating this class does not return a value.
    """

    verbosity: int | VerbosityMode = field(
        default_factory=lambda: Env.get("TESTING_VERBOSITY", VerbosityMode.DETAILED),
        metadata={
            "description": (
                "Level of detail in test output. 0: silent, 1: standard, 2: detailed. "
                "Defaults to 2 (detailed)."
            ),
            "default": 2,
        },
    )

    fail_fast: bool = field(
        default_factory=lambda: Env.get("TESTING_FAIL_FAST", False),
        metadata={
            "description": (
                "If True, stops execution at the first failure. Defaults to False."
            ),
            "default": False,
        },
    )

    start_dir: str = field(
        default_factory=lambda: Env.get("TESTING_START_DIR", "tests"),
        metadata={
            "description": ("Directory to search for tests. Defaults to 'tests'."),
            "default": "tests",
        },
    )

    file_pattern: str = field(
        default_factory=lambda: Env.get("TESTING_FILE_PATTERN", "test_*.py"),
        metadata={
            "description": (
                "Filename pattern to identify test files. Defaults to 'test_*.py'."
            ),
            "default": "test_*.py",
        },
    )

    method_pattern: str = field(
        default_factory=lambda: Env.get("TESTING_METHOD_PATTERN", "test*"),
        metadata={
            "description": (
                "Pattern to filter specific test methods. Defaults to 'test*'."
            ),
            "default": "test*",
        },
    )

    cache_results: bool = field(
        default_factory=lambda: Env.get("TESTING_CACHE_RESULTS", False),
        metadata={
            "description": ("Save a JSON file with the test results."),
            "default": False,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate runner options and normalize verbosity after construction.

        Returns
        -------
        None
            This method performs validation and normalization and returns None.

        Raises
        ------
        ValueError
            If any of the runner options are invalid.
        """
        super().__post_init__()
        verbosity = self.verbosity
        if isinstance(verbosity, VerbosityMode):
            verbosity = verbosity.value
        validate_integer(verbosity, "verbosity")
        if verbosity not in _VERBOSITY_VALUES:
            message = "verbosity must be a valid VerbosityMode value."
            raise ValueError(message)
        object.__setattr__(self, "verbosity", verbosity)
        validate_boolean(self.fail_fast, "fail_fast")
        validate_boolean(self.cache_results, "cache_results")
        for name in ("start_dir", "file_pattern", "method_pattern"):
            validate_string(getattr(self, name), name)
