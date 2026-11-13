# ruff: noqa: ANN401, TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
# Preserve heterogeneous template payload values.
"""Provide view globals operations through ``_global_config``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from orionis.foundation.contracts.application import IApplication


def _global_config(app: IApplication) -> Callable[..., Any]:
    """
    Build the ``config`` template global bound to the application.

    Parameters
    ----------
    app : orionis.IApplication
        Application container providing configuration access.

    Returns
    -------
    collections.abc.Callable
        Callable that retrieves a dot-separated configuration key.
    """

    def config(key: str, default: Any = None) -> Any:
        """
        Retrieve an application configuration value.

        Parameters
        ----------
        key : str
            Dot-separated configuration key (e.g. ``'app.name'``).
        default : typing.Any, optional
            Value returned when the key is absent.

        Returns
        -------
        typing.Any
            Configuration value or *default*.
        """
        cnf_value = app.config(key)
        return cnf_value if cnf_value is not None else default

    return config
