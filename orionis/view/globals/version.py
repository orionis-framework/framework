from __future__ import annotations
import sys
from typing import Any

# ruff: noqa: ANN401, PLC0415

def _global_python_version() -> Any:
    """
    Build the ``python_version`` template global.

    Returns
    -------
    Any
        Callable that returns the Python version.
    """
    def python_version() -> str:
        """
        Return the Python version.

        Returns
        -------
        str
            Python version in ``X.X.X`` format.
        """
        major = sys.version_info.major
        minor = sys.version_info.minor
        micro = sys.version_info.micro

        return f"{major}.{minor}.{micro}"

    return python_version

def _global_framework_version() -> Any:
    """
    Build the ``framework_version`` template global.

    Returns
    -------
    Any
        Callable that returns the framework version.
    """
    def framework_version() -> str:
        """
        Return the framework version.

        Returns
        -------
        str
            Framework version in ``X.X.X`` format.
        """
        from orionis.metadata import VERSION
        return VERSION

    return framework_version
