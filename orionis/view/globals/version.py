# ruff: noqa: TC003
# Keep public callback and application annotations resolvable at runtime.
"""Provide view globals operations.

Includes ``_global_python_version``, ``_global_framework_version``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from orionis import metadata


def _global_python_version() -> Callable[[], str]:
    """
    Build the ``python_version`` template global.

    Returns
    -------
    collections.abc.Callable
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


def _global_framework_version() -> Callable[[], str]:
    """
    Build the ``framework_version`` template global.

    Returns
    -------
    collections.abc.Callable
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
        return metadata.VERSION

    return framework_version
