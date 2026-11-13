# ruff: noqa: ANN401, PLC0415
# Resolve optional backend classes dynamically without importing them during discovery.
"""Provide shared hashing limits and lazy backend resolution."""

import importlib
from typing import Any
from orionis.hashing.exceptions import MissingHashDependencyException

ARGON2_MAX_COST = 2**32 - 1
"""Largest memory or time cost representable by the native Argon2 interface."""
ARGON2_MAX_THREADS = 2**24 - 1
"""Largest number of parallel lanes supported by Argon2."""
ARGON2_MEMORY_PER_THREAD = 8
"""Minimum memory in kibibytes required for each Argon2 lane."""


def import_hasher_backend(module: str, attribute: str, package: str) -> Any:
    """
    Import the backend class of a hashing driver on demand.

    Parameters
    ----------
    module : str
        Fully qualified module exposing the backend class.
    attribute : str
        Name of the backend class inside ``module``.
    package : str
        Distribution requirement used in the uv hint when the import fails.

    Returns
    -------
    typing.Any
        The backend class ready to be instantiated.

    Raises
    ------
    orionis.hashing.exceptions.MissingHashDependencyException
        If the backend package is not installed.
    """
    from pwdlib.exceptions import HasherNotAvailable

    try:
        imported = importlib.import_module(module)
    except (ImportError, HasherNotAvailable) as exc:
        error_msg = (  # NOSONAR(S1110) - Preserve multiline grouping.
            f"The '{package}' package is required by this hashing driver. "
            f"Install it with: uv add '{package}'"
        )
        raise MissingHashDependencyException(error_msg) from exc

    return getattr(imported, attribute)
